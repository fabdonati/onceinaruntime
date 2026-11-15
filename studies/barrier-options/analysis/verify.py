"""Check every C++ payoff and termination decision against an independent oracle."""
import argparse
import hashlib
import json
import math
from decimal import Decimal, localcontext
from pathlib import Path
import subprocess
import numpy as np
from model import DISCOUNT, generate, oracle, vanilla_diagnostic

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def audit_output(prefix, reference):
    for suffix, dtype, expected in zip(("payoffs.f64","lifetimes.u64","knocked.u8"),
                                        ("<f8","<u8","u1"), reference):
        actual = np.fromfile(str(prefix)+"."+suffix, dtype=dtype)
        if not np.array_equal(actual, expected):
            raise AssertionError(f"{prefix}: mismatch in {suffix}")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--binary",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args(); a.output.mkdir(parents=True,exist_ok=False)
    report={"numpy":np.__version__,"binary_sha256":digest(a.binary),"status":"running","executions":[]}
    def save(): (a.output/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    save()
    try:
        # Exactly representable data let Decimal audit the oracle without a tolerance.
        tiny=np.array([[2,.5,1],[1,1,2],[1,1,1],[.5,1,1],[1.25,1,1],[1,2.5,.5],[1,1.5,1]])
        expected=np.array([0,0,1,0,2,0,3.])
        got=oracle(tiny,16,.5,8,6)
        assert np.array_equal(got[0],expected)
        assert got[1].tolist()==[1,3,3,3,3,2,3] and got[2].tolist()==[1,1,0,0,0,1,0]
        with localcontext() as ctx:
            ctx.prec=60
            for row, payoff in zip(tiny,expected):
                s=Decimal(8); dead=False
                for f in row:
                    s*=Decimal.from_float(float(f)); dead |= s>=16
                exact=Decimal(0) if dead else Decimal('.5')*max(s-6,Decimal(0))
                assert float(exact)==payoff
        report["decimal_literal_oracle"]="passed"
        fixtures=[("literal",tiny,200.,1.)]
        fixtures += [(f"tail-{n}",generate(n,17,29),120.,DISCOUNT) for n in (0,1,2,3,7,19)]
        fixtures += [("deterministic",generate(17,252,11,sigma=0.),120.,DISCOUNT)]
        for seed in (11,29,47):
            factors=generate(8192,252,seed)
            for b in (100.,105.,120.,150.,math.inf):
                fixtures.append((f"seed-{seed}-barrier-{b}",factors,b,DISCOUNT))
        report["vanilla_diagnostic"]=vanilla_diagnostic(fixtures[-1][1])
        for name,factors,b,discount in fixtures:
            reference=oracle(factors,b,discount)
            for layout,array in (("path",factors),("step",np.ascontiguousarray(factors.T))):
                file=a.output/(name+"-"+layout+".f64"); array.tofile(file)
                for method in ("scalar","fixed","refill"):
                    prefix=a.output/(name+"-"+layout+"-"+method)
                    cmd=[str(a.binary.resolve()),str(file.resolve()),str(len(factors)),str(factors.shape[1]),layout,method,str(b),str(discount),str(prefix.resolve())]
                    r=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
                    Path(str(prefix)+".stdout.json").write_text(r.stdout)
                    Path(str(prefix)+".stderr.txt").write_text(r.stderr)
                    entry={"command":cmd,"returncode":r.returncode,"input_sha256":digest(file),"checked_paths":len(factors)}
                    report["executions"].append(entry);save();r.check_returncode()
                    audit_output(prefix,reference)
                    entry["all_payoffs_and_stop_decisions_exact"]=True
                    save()
                # Canonical random inputs are retained once per seed in the pilot;
                # this correctness suite retains input hashes and generator source.
                file.unlink()
        report["status"]="passed"
    except BaseException as error:
        report.update(status="failed",error=repr(error)); raise
    finally: save()
    print(f"Passed {len(report['executions'])} separate checks, every payoff/date/KO exact; Decimal fixtures passed")

if __name__=="__main__": main()
