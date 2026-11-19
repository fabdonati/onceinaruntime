"""One fresh-process whole-valuation observation; no file/IPC cost in its interval."""
import argparse
import ctypes as ct
import hashlib
import json
import platform
import resource
import time
from pathlib import Path
import numpy as np
from model import DISCOUNT, generate

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("library","canonical","reference","output"):
        p.add_argument("--"+name,type=Path,required=True)
    for name in ("paths","steps","seed"):
        p.add_argument("--"+name,type=int,required=True)
    p.add_argument("--barrier",type=float,required=True)
    p.add_argument("--layout",choices=("path","step"),required=True)
    p.add_argument("--method",choices=("scalar","fixed","refill"),required=True)
    a=p.parse_args()
    lib=ct.CDLL(str(a.library.resolve()))
    f=lib.barrier_evaluate
    pointer=ct.POINTER(ct.c_double)
    f.argtypes=[pointer,ct.c_size_t,ct.c_size_t,ct.c_int,ct.c_int,ct.c_double,ct.c_double,pointer,pointer]
    f.restype=ct.c_int
    reference=np.fromfile(a.reference,dtype="<f8")
    canonical_hash=hashlib.sha256(a.canonical.read_bytes()).hexdigest()
    method=("scalar","fixed","refill").index(a.method)
    layout=("path","step").index(a.layout)
    def valuation():
        start=time.perf_counter_ns()
        factors=generate(a.paths,a.steps,a.seed)
        generated=time.perf_counter_ns()
        inputs=factors if layout==0 else np.ascontiguousarray(factors.T)
        arranged=time.perf_counter_ns()
        output=np.empty(a.paths,dtype=np.float64)
        price=ct.c_double()
        status=f(inputs.ctypes.data_as(pointer),a.paths,a.steps,layout,method,a.barrier,DISCOUNT,
                 output.ctypes.data_as(pointer),ct.byref(price))
        end=time.perf_counter_ns()
        return factors,inputs,output,price.value,status,{
            "complete_ns":end-start,"generation_ns":generated-start,
            "layout_ns":arranged-generated,"output_allocation_bridge_compute_ns":end-arranged}
    def check(v):
        factors,inputs,output,price,status,_=v
        if status or hashlib.sha256(factors).hexdigest()!=canonical_hash or not np.array_equal(output,reference):
            raise AssertionError("complete valuation input/output mismatch")
        ordered=0.
        for value in reference: ordered+=float(value)
        if price!=(ordered/a.paths if a.paths else 0.): raise AssertionError("aggregate mismatch")
    warm=valuation();check(warm);del warm
    result=valuation();check(result)
    factors,inputs,output,price,status,phases=result
    output.tofile(a.output)
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(json.dumps({**phases,"method":a.method,"layout":a.layout,"seed":a.seed,"paths":a.paths,
                      "steps":a.steps,"barrier":a.barrier,"price":price,"validated":True,
                      "canonical_sha256":canonical_hash,"layout_sha256":hashlib.sha256(inputs).hexdigest(),
                      "payoffs_sha256":hashlib.sha256(output).hexdigest(),
                      "process_peak_rss_bytes":rss if platform.system()=="Darwin" else rss*1024,
                      "input_buffer_bytes":int(factors.nbytes+(inputs.nbytes if layout else 0)),
                      "output_bytes":int(output.nbytes),"numpy":np.__version__,
                      "scope":"RNG construction, canonical allocation/generation, layout conversion allocation, output allocation, ctypes call, kernel and ordered aggregation; excludes imports/library load, validation, serialization and buffer destruction"}))

if __name__=="__main__": main()
