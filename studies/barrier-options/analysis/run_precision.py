"""Prepare, verify or measure a bounded float/double comparison in fresh processes."""
import argparse
import csv
import datetime as dt
import gc
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import zipfile

import numpy as np
from model import DISCOUNT, generate, oracle
from precision_model import oracle32, ordered_mean, errors
from run_pilot import ROOT, HERE, command, digest, source_files
from run_main import environment, power_is_stable, rss_peaks

GIB = 1024 ** 3
CANDIDATES = [(p, m) for m in ('scalar', 'fixed', 'refill') for p in ('f64', 'f32')]
DTYPE = {'f64': '<f8', 'f32': '<f4', 'f64-rounded': '<f8'}


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def validate_config(cfg):
    required = dict(kind='float-double prepared-input timing pilot', paths=8192, steps=252,
                    seeds=[11, 29, 47], barriers=[105, 120, 150], layouts=['path', 'step'],
                    precisions=['f64', 'f32'], methods=['scalar', 'fixed', 'refill'], repeats=6,
                    maximum_seconds=1800, maximum_evidence_bytes=GIB,
                    maximum_combined_peak_rss_bytes=GIB, maximum_start_load_per_cpu=.5)
    if any(cfg.get(k) != v for k, v in required.items()):
        raise ValueError('precision pilot matrix/budget differs from the declared brief')


def execution_plan(cfg):
    result = []
    for si, seed in enumerate(cfg['seeds']):
        for ci, (barrier, layout) in enumerate((b, l) for b in cfg['barriers'] for l in cfg['layouts']):
            for repeat in range(cfg['repeats']):
                shift = (si + ci + repeat) % len(CANDIDATES)
                order = CANDIDATES[shift:] + CANDIDATES[:shift]
                for position, (precision, method) in enumerate(order):
                    result.append(dict(id=f's{seed}-b{barrier}-{layout}-r{repeat}-{precision}-{method}',
                                       seed=seed, barrier=barrier, layout=layout, repeat=repeat,
                                       precision=precision, method=method, order_position=position))
    return result


def artifact_paths(build):
    extension = '.dylib' if sys.platform == 'darwin' else '.so'
    return [build/'bin/barrier_precision_bench', build/'lib'/('libbarrier_core'+extension),
            build/'lib'/('libbarrier_float_core'+extension)]


def build_issues(build, timing):
    issues = []
    try:
        cache = (build/'CMakeCache.txt').read_text()
    except OSError:
        return ['missing build cache; build a precision preset first']
    for setting in ('OIR_BARRIER_PRECISION:BOOL=ON\n', 'OIR_BARRIER_SIMD:BOOL=ON\n'):
        if setting not in cache:
            issues.append('required build setting missing: '+setting.strip())
    if timing and ('CMAKE_BUILD_TYPE:STRING=Release\n' not in cache or 'MEASURED_SANITIZERS:BOOL=OFF\n' not in cache):
        issues.append('timing requires Release without sanitizers')
    for path in [*artifact_paths(build), build/'compile_commands.json']:
        if not path.is_file():
            issues.append('missing build artifact: '+str(path))
    binary = build/'bin/barrier_precision_bench'
    if binary.is_file():
        dependencies = [* (HERE.parent/'src').glob('*.cpp'), * (HERE.parent/'src').glob('*.hpp'),
                        HERE.parent/'precision/precision.cpp', HERE.parent/'precision/precision.hpp', HERE.parent/'precision/benchmark.cpp']
        if any(p.stat().st_mtime_ns > binary.stat().st_mtime_ns for p in dependencies):
            issues.append('pricing source is newer than executable; rebuild the precision preset')
    return issues


def audit(prefix, precision, reference):
    files = []
    for suffix, dtype, expected in zip((f'payoffs.{precision}', 'lifetimes.u64', 'knocked.u8'),
                                       (DTYPE[precision], '<u8', 'u1'), reference):
        path = Path(str(prefix)+'.'+suffix)
        actual = np.fromfile(path, dtype=dtype)
        if not np.array_equal(actual, expected):
            raise RuntimeError('independent '+precision+' reference mismatch: '+str(path))
        files.append(dict(name=path.name, bytes=path.stat().st_size, sha256=digest(path)))
    return files


def check_observation(actual, item, cfg, reference, timed):
    for key in ('precision', 'method', 'layout', 'barrier'):
        if actual.get(key) != item[key]:
            raise RuntimeError('worker identity mismatch: '+key)
    if any(actual.get(k) != cfg[k] for k in ('paths', 'steps')):
        raise RuntimeError('worker dimensions mismatch')
    if actual.get('timed') is not timed or not actual.get('validated_cpp'):
        raise RuntimeError('worker timing/validation mismatch')
    ns = actual.get('prepared_ns')
    if type(ns) is not int or (ns <= 0 if timed else ns != 0):
        raise RuntimeError('invalid timing observation')
    if not math.isfinite(actual.get('price', math.nan)) or actual['price'] != ordered_mean(reference[0]):
        raise RuntimeError('ordered aggregate differs from independent reference')
    expected_bytes = cfg['paths']*cfg['steps']*np.dtype(DTYPE[item['precision']]).itemsize
    if actual.get('input_bytes') != expected_bytes:
        raise RuntimeError('input storage size mismatch')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true', help='preflight only; no datasets or timing workers')
    mode.add_argument('--smoke', action='store_true', help='untimed 257-path end-to-end harness check')
    mode.add_argument('--verify', action='store_true', help='untimed complete oracle matrix, one execution per candidate/case')
    mode.add_argument('--run', action='store_true', help='run the frozen prepared-input timing pilot once')
    parser.add_argument('--build', type=Path, default=ROOT/'build/precision-release')
    parser.add_argument('--config', type=Path, default=HERE.parent/'configs/precision-pilot.json')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text()); validate_config(cfg)
    timing = args.run
    build = args.build.resolve()
    entry = environment('preflight')
    load_limit = (entry['cpu_count'] or 1)*cfg['maximum_start_load_per_cpu']
    issues = build_issues(build, timing or args.check)
    if timing or args.check:
        if not power_is_stable(entry['power']): issues.append('stable AC charging/charged required')
        if entry['load_average'][0] > load_limit: issues.append(f'one-minute start load exceeds {load_limit:g}')
    if args.check:
        print(json.dumps(dict(ready=not issues, issues=issues, environment=entry, start_load_limit=load_limit,
                              planned_observations=len(execution_plan(cfg)), timing_scope=cfg['scope']), indent=2))
        return 0 if not issues else 2
    if args.output is None: parser.error('--output is required for execution')
    if args.smoke:
        cfg = cfg | dict(kind='untimed precision smoke', paths=257, steps=17, seeds=[11], barriers=[120], repeats=1, maximum_seconds=120)
    elif args.verify:
        cfg = cfg | dict(kind='untimed precision oracle verification', repeats=1)
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=False)
    plan = execution_plan(cfg)
    binary = build/'bin/barrier_precision_bench'
    snapshots = source_files()
    artifacts = {str(p): digest(p) for p in artifact_paths(build) if p.is_file()}
    manifest = dict(status='preflight', started_utc=utc(), command=[sys.executable,*sys.argv], cwd=str(Path.cwd()),
                    config=cfg, config_sha256=digest(args.config), source_sha256=snapshots, executable_sha256=artifacts,
                    git_revision=command(['git','rev-parse','HEAD']), git_state=command(['git','status','--porcelain=v1','--untracked-files=all']),
                    compiler=command(['g++-16','--version']), python=sys.version, numpy=np.__version__, platform=platform.platform(),
                    timed=timing, environment=[entry], start_load_limit=load_limit, preflight_issues=issues,
                    datasets=[], references=[], executions=[], observations=0, expected_observations=len(plan), accuracy=[],
                    limitations=['FP32 changes input storage, arithmetic, native width and possibly path decisions together.',
                                 'Both precisions use ascending-ID FP64 aggregation.',
                                 'No complete-valuation timing in this extension.',
                                 'Three input seeds reused across process timings; no tail or independent-population claim.',
                                 'No sample replacements or automatic rerun.'])
    observations=[]; references={}; clock=time.monotonic(); owned_locks=[]

    def save():
        manifest['observations']=len(observations)
        (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

    def resources():
        elapsed=time.monotonic()-clock
        size=sum(p.stat().st_size for p in output.rglob('*') if p.is_file())
        peaks=rss_peaks()
        manifest['latest_resources']=peaks | dict(elapsed_seconds=elapsed,evidence_bytes=size)
        if elapsed >= cfg['maximum_seconds']: raise RuntimeError('precision campaign time cap reached')
        if size >= cfg['maximum_evidence_bytes']: raise RuntimeError('precision evidence cap reached')
        if peaks['conservative_combined_peak_bytes'] >= cfg['maximum_combined_peak_rss_bytes']: raise RuntimeError('precision process-memory cap reached')

    def sample(label, start_gate=False):
        record=environment(label);manifest['environment'].append(record);save();resources()
        if timing:
            if not power_is_stable(record['power']): raise RuntimeError('power left stable AC')
            if start_gate and record['load_average'][0] > load_limit: raise RuntimeError('observation entry load exceeds declared gate')

    def run(cmd,label):
        record=dict(id=label,command=list(map(str,cmd)),started_utc=utc())
        manifest['executions'].append(record);save()
        remaining=cfg['maximum_seconds']-(time.monotonic()-clock)
        try:
            result=subprocess.run(record['command'],capture_output=True,text=True,timeout=max(.01,min(60,remaining)))
            record['returncode']=result.returncode
            (output/(label+'.stdout.json')).write_text(result.stdout)
            (output/(label+'.stderr.txt')).write_text(result.stderr)
            record['stdout_sha256']=digest(output/(label+'.stdout.json'))
            record['stderr_sha256']=digest(output/(label+'.stderr.txt'))
            result.check_returncode()
            return json.loads(result.stdout),record
        except subprocess.TimeoutExpired as error:
            record['error']='worker timeout'
            for suffix,value in (('stdout',error.stdout),('stderr',error.stderr)):
                path=output/(label+'.'+suffix+'.txt')
                path.write_bytes(value if isinstance(value,bytes) else (value or '').encode())
            raise
        finally:
            record['finished_utc']=utc();save()

    save()
    try:
        if issues:
            manifest['status']='not_started'
            print('Precision run held: '+'; '.join(issues),file=sys.stderr)
            return 2
        if timing:
            if list((ROOT/'build').glob('*/.main-campaign.lock')):
                raise RuntimeError('another barrier timing campaign has a lock')
            # Share the original runner's default lock as well as this build's lock.
            for lock in dict.fromkeys((ROOT/'build/barrier-release/.main-campaign.lock',build/'.main-campaign.lock')):
                lock.parent.mkdir(parents=True,exist_ok=True)
                fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);owned_locks.append(lock)
                with os.fdopen(fd,'w') as f:json.dump(dict(pid=os.getpid(),output=str(output)),f)
        if shutil.disk_usage(output).free < 2*GIB:raise RuntimeError('requires 2 GiB free disk reserve')
        with zipfile.ZipFile(output/'source.zip','w',zipfile.ZIP_DEFLATED) as archive:
            for name in snapshots:archive.write(ROOT/name,arcname=name)
        manifest['source_archive_sha256']=digest(output/'source.zip')
        for name in ('CMakeCache.txt','compile_commands.json'):shutil.copyfile(build/name,output/name)
        info,_=run([binary,'--info'],'info');manifest['native_types']=info
        if timing:
            manifest['background_before']=command(['ps','-Ao','pcpu,comm'])
            manifest['thermal_before']=command(['pmset','-g','therm'])
            manifest['timer'],_=run([build/'bin/barrier_bench','--timer'],'timer')
        for seed in cfg['seeds']:
            sample(f'prepare seed {seed}')
            canonical=generate(cfg['paths'],cfg['steps'],seed)
            rounded=canonical.astype('<f4')
            widened=rounded.astype('<f8')
            for precision,array in (('f64',canonical),('f32',rounded)):
                for layout,values in (('path',array),('step',np.ascontiguousarray(array.T))):
                    path=output/f'seed-{seed}-{layout}.{precision}';values.tofile(path)
                    manifest['datasets'].append(dict(seed=seed,precision=precision,layout=layout,name=path.name,
                                                     bytes=path.stat().st_size,sha256=digest(path)))
            for barrier in cfg['barriers']:
                refs={'f64':oracle(canonical,barrier),'f32':oracle32(rounded,barrier),'f64-rounded':oracle(widened,barrier)}
                for precision,ref in refs.items():
                    files=[]
                    for suffix,values in zip((f'payoffs.{"f32" if precision=="f32" else "f64"}','lifetimes.u64','knocked.u8'),ref):
                        path=output/f'ref-{seed}-{barrier}-{precision}.{suffix}';values.tofile(path)
                        files.append(dict(name=path.name,bytes=path.stat().st_size,sha256=digest(path)))
                    manifest['references'].append(dict(seed=seed,barrier=barrier,precision=precision,files=files))
                    references[seed,barrier,precision]=ref
                for comparison,candidate,reference in (('total-f32-vs-f64','f32','f64'),('input-rounding-only','f64-rounded','f64'),('remaining-arithmetic','f32','f64-rounded')):
                    manifest['accuracy'].append(dict(seed=seed,barrier=barrier,comparison=comparison,**errors(refs[candidate],refs[reference])))
            del canonical,rounded,widened,refs,ref,values,array
            gc.collect();resources();save()
        for item in plan:
            item['command']=list(map(str,[binary,item['precision'],output/f"seed-{item['seed']}-{item['layout']}.{item['precision']}",
                                         cfg['paths'],cfg['steps'],item['layout'],item['method'],item['barrier'],DISCOUNT,output/item['id']]))
            if timing:item['command'].append('--time')
        (output/'execution-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
        manifest['execution_plan_sha256']=digest(output/'execution-plan.json')
        manifest['frozen_before_workers_utc']=utc();sample('before workers',start_gate=True)
        manifest['status']='running';save()
        group=None
        for item in plan:
            key=(item['seed'],item['barrier'],item['layout'],item['repeat'])
            if key!=group:
                sample(str(key));group=key
                if source_files()!=snapshots or any(digest(Path(p))!=h for p,h in artifacts.items()):raise RuntimeError('frozen executable/source changed')
            actual,record=run(item['command'],item['id'])
            reference=references[item['seed'],item['barrier'],item['precision']]
            check_observation(actual,item,cfg,reference,timing)
            expected_width=info['float_lanes' if item['precision']=='f32' else 'double_lanes']
            if actual['native_width']!=expected_width:raise RuntimeError('worker SIMD width mismatch')
            record['audited_outputs']=audit(output/item['id'],item['precision'],reference)
            record['all_ordered_payoffs_dates_knockouts_exact']=True
            observations.append({k:item[k] for k in ('id','seed','repeat','order_position')} | actual)
            (output/'observations.json').write_text(json.dumps(observations,indent=2)+'\n');save();resources()
            if item['order_position']==5:print(f"Audited {len(observations)}/{len(plan)} precision observations",flush=True)
        sample('finished')
        for dataset in manifest['datasets']:
            if digest(output/dataset['name'])!=dataset['sha256']:raise RuntimeError('input hash changed')
        for reference in manifest['references']:
            for file in reference['files']:
                if digest(output/file['name'])!=file['sha256']:raise RuntimeError('reference hash changed')
        if source_files()!=snapshots or any(digest(Path(p))!=h for p,h in artifacts.items()):raise RuntimeError('final executable/source mismatch')
        (output/'accuracy.json').write_text(json.dumps(manifest['accuracy'],indent=2)+'\n')
        with (output/'accuracy.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(manifest['accuracy'][0]));writer.writeheader();writer.writerows(manifest['accuracy'])
        if len(observations)!=len(plan):raise RuntimeError('incomplete precision matrix')
        manifest['status']='complete';manifest['final_integrity']='passed';resources()
        return 0
    except BaseException as error:
        manifest.update(status='failed',error=repr(error));raise
    finally:
        manifest['finished_utc']=utc();manifest['elapsed_seconds']=time.monotonic()-clock;save()
        for lock in owned_locks:lock.unlink()


if __name__=='__main__':
    sys.exit(main())
