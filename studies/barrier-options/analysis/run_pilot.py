"""Retain one bounded, sequential pilot with canonical data and source snapshots."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import zipfile
import numpy as np
from model import DISCOUNT, generate, oracle, vanilla_diagnostic
from verify import audit_output

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def command(cmd):
    try:
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=15)
        return dict(command=cmd,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
    except (OSError,subprocess.TimeoutExpired) as error:
        return dict(command=cmd,error=repr(error))
def source_files():
    paths=[ROOT/'CMakeLists.txt',ROOT/'CMakePresets.json',ROOT/'publication/visual-style.json']
    paths.extend(p for p in (ROOT/'studies/barrier-options').rglob('*')
                 if p.is_file() and '__pycache__' not in p.parts and p.suffix in ('.cpp','.hpp','.py','.json','.txt'))
    return {str(p.relative_to(ROOT)):digest(p) for p in sorted(paths)}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,default=ROOT/'build/barrier-release')
    p.add_argument('--config',type=Path,default=HERE.parent/'configs/pilot.json')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); a.build=a.build.resolve(); a.output=a.output.resolve()
    cache=(a.build/'CMakeCache.txt').read_text()
    for setting in ('CMAKE_BUILD_TYPE:STRING=Release\n','MEASURED_SANITIZERS:BOOL=OFF\n','OIR_BARRIER_SIMD:BOOL=ON\n'):
        if setting not in cache:p.error('requires barrier-release without sanitizers')
    cfg=json.loads(a.config.read_text())
    if (cfg['paths'],cfg['steps'],cfg['seeds'],cfg['barriers'],cfg['process_repeats_per_seed_case'])!=(8192,252,[11,29,47],[105,120,150],3):
        p.error('pilot budget is frozen; use a separately agreed campaign for other sizes/repeats')
    if cfg['layouts']!=['path','step'] or cfg['methods']!=['scalar','fixed','refill']:
        p.error('unexpected pilot matrix')
    a.output.mkdir(parents=True,exist_ok=False)
    binary=a.build/'bin/barrier_bench'
    library=a.build/'lib'/('libbarrier_core.dylib' if sys.platform=='darwin' else 'libbarrier_core.so')
    before=source_files()
    manifest={'status':'running','started_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
              'command':[sys.executable,*sys.argv],'cwd':str(Path.cwd()),'config':cfg,'config_sha256':digest(a.config),
              'source_sha256':before,'binary_sha256':digest(binary),'library_sha256':digest(library),
              'python':sys.version,'numpy':np.__version__,'platform':platform.platform(),
              'git_revision':command(['git','rev-parse','HEAD']),
              'git_state':command(['git','status','--porcelain=v1','--untracked-files=all']),
              'compiler':command(['g++-16','--version']),'environment':[],
              'datasets':[],'executions':[],
              'limits':['Single thread; no affinity, core, temperature or frequency control.',
                        'Warm-up and correctness checks touch data; no cache-residency claim.',
                        'Three repeats per seed/configuration characterize scale; no tail or production-latency claim.',
                        'Prepared and whole-valuation scopes run in separate sequential fresh processes.',
                        'The whole-valuation scope includes the Python generator and ctypes bridge; buffer destruction excluded.',
                        'All attempts retained. Stop on failure or observed power instability; never replace slow samples.']}
    def save(): (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    def environment(label):
        power=command(['pmset','-g','batt']) if sys.platform=='darwin' else None
        manifest['environment'].append({'label':label,'utc':dt.datetime.now(dt.timezone.utc).isoformat(),
                                        'load_average':os.getloadavg(),'power':power})
        save()
        if power and (power.get('returncode')!=0 or "'AC Power'" not in power['stdout'] or 'discharging' in power['stdout']):
            raise RuntimeError('AC/stable-power requirement not met; pilot stopped')
    def run(cmd,label):
        record={'id':label,'command':list(map(str,cmd)),'started_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
        manifest['executions'].append(record);save()
        try:
            result=subprocess.run(record['command'],capture_output=True,text=True,timeout=60)
            (a.output/(label+'.stdout.json')).write_text(result.stdout)
            (a.output/(label+'.stderr.txt')).write_text(result.stderr)
            record.update(returncode=result.returncode,finished_utc=dt.datetime.now(dt.timezone.utc).isoformat());save()
            result.check_returncode()
            return json.loads(result.stdout)
        except BaseException as error:
            record['error']=repr(error);save();raise
    save()
    try:
        environment('before preparation')
        with zipfile.ZipFile(a.output/'source.zip','w',zipfile.ZIP_DEFLATED) as archive:
            for name in before:archive.write(ROOT/name,arcname=name)
        manifest['source_archive_sha256']=digest(a.output/'source.zip')
        for name in ('CMakeCache.txt','compile_commands.json'):
            shutil.copyfile(a.build/name,a.output/name)
        manifest['background_before']=command(['ps','-Ao','pcpu,comm'])
        manifest['thermal_before']=command(['pmset','-g','therm']) if sys.platform=='darwin' else None
        manifest['memory_before']=command(['vm_stat']) if sys.platform=='darwin' else None
        manifest['cpp_timer']=run([binary,'--timer'],'timer')
        deltas=[];previous=time.perf_counter_ns()
        for _ in range(10000):
            current=time.perf_counter_ns();deltas.append(current-previous);previous=current
        manifest['python_clock']={'info':str(time.get_clock_info('perf_counter')),'deltas_ns':deltas}
        save()
        # Complete all data preparation and references before the observation matrix.
        references={}
        for seed in cfg['seeds']:
            factors=generate(cfg['paths'],cfg['steps'],seed)
            files={}
            for layout,data in (('path',factors),('step',np.ascontiguousarray(factors.T))):
                file=a.output/f'seed-{seed}-{layout}.f64';data.tofile(file);files[layout]=file
            manifest['datasets'].append({'seed':seed,'paths':cfg['paths'],'steps':cfg['steps'],
                                         'files':{k:{'name':v.name,'sha256':digest(v),'bytes':v.stat().st_size} for k,v in files.items()},
                                         'vanilla':vanilla_diagnostic(factors)})
            for b in cfg['barriers']:
                ref=oracle(factors,b);references[seed,b]=ref
                for suffix,values in zip(('payoffs.f64','lifetimes.u64','knocked.u8'),ref):
                    values.tofile(a.output/f'ref-{seed}-{b}.{suffix}')
            save()
        del factors,data
        observations=[]
        environment('before observations')
        for si,seed in enumerate(cfg['seeds']):
            for ci,(b,layout) in enumerate((b,l) for b in cfg['barriers'] for l in cfg['layouts']):
                for repeat in range(3):
                    environment(f'seed {seed} barrier {b} layout {layout} repeat {repeat}')
                    shift=(si+ci+repeat)%3
                    order=cfg['methods'][shift:]+cfg['methods'][:shift]
                    for position,method in enumerate(order):
                        label=f's{seed}-b{b}-{layout}-r{repeat}-{method}'
                        prefix=a.output/label
                        prepared=run([binary,a.output/f'seed-{seed}-{layout}.f64',cfg['paths'],cfg['steps'],layout,method,b,DISCOUNT,prefix,'--time'],label+'-prepared')
                        audit_output(prefix,references[seed,b])
                        if prepared['prepared_ns']<=0:raise RuntimeError('nonpositive operation duration')
                        whole=run([sys.executable,HERE/'valuation.py','--library',library,
                                   '--canonical',a.output/f'seed-{seed}-path.f64',
                                   '--reference',a.output/f'ref-{seed}-{b}.payoffs.f64',
                                   '--output',a.output/(label+'-complete.payoffs.f64'),
                                   '--paths',cfg['paths'],'--steps',cfg['steps'],'--seed',seed,'--barrier',b,
                                   '--layout',layout,'--method',method],label+'-complete')
                        if not whole['validated']:raise RuntimeError('whole valuation check failed')
                        observations.append({'id':label,'seed':seed,'repeat':repeat,'order_position':position,
                                             **prepared,'complete':whole})
                        (a.output/'observations.json').write_text(json.dumps(observations,indent=2)+'\n')
                print(f'Saved seed {seed}, barrier {b}, {layout}: {len(observations)} paired-scope observations',flush=True)
        environment('after observations')
        if before!=source_files() or digest(binary)!=manifest['binary_sha256'] or digest(library)!=manifest['library_sha256']:
            raise RuntimeError('source or executable changed during pilot')
        manifest.update(status='complete',observation_count=len(observations),pricing_processes=2*len(observations))
    except BaseException as error:
        manifest.update(status='failed',error=repr(error));raise
    finally:
        manifest['finished_utc']=dt.datetime.now(dt.timezone.utc).isoformat();save()
    print('Pilot complete; raw observations retained; main campaign not run.')

if __name__=='__main__':main()
