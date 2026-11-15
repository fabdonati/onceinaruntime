"""Verify a frozen synthetic matrix, or run its bounded pilot/main campaign."""
import argparse
import csv
import datetime as dt
import hashlib
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

from inputs import synthetic, write_bars
from reference import replay

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
ROOT = STUDY.parents[1]
CANDIDATES = [('strategy', 'history'), ('event', 'history'),
              ('strategy', 'snapshot'), ('event', 'snapshot')]
# Each candidate occupies each position once; all ordered immediate predecessor
# pairs occur once in this four-row Williams design.
ORDERS = [(0,1,3,2), (1,2,0,3), (2,3,1,0), (3,0,2,1)]
INTEGER_FIELDS = {'config','fast','slow','trades'}


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def command(argv):
    try:
        result = subprocess.run(list(map(str, argv)), capture_output=True, text=True, timeout=15)
        return dict(command=list(map(str, argv)), returncode=result.returncode,
                    stdout=result.stdout, stderr=result.stderr)
    except (OSError, subprocess.TimeoutExpired) as error:
        return dict(command=list(map(str, argv)), error=repr(error))


def environment():
    result = dict(utc=utc(), platform=platform.platform(), cpu_count=os.cpu_count(),
                  load_average=list(os.getloadavg()), power=command(['pmset','-g','batt']))
    return result


def source_files():
    files = [ROOT/'CMakeLists.txt', ROOT/'CMakePresets.json', STUDY/'CMakeLists.txt']
    for folder in ('src','tests','analysis','configs'):
        files.extend(p for p in (STUDY/folder).rglob('*')
                     if p.is_file() and p.suffix in ('.cpp','.hpp','.py','.json'))
    return {str(p.relative_to(ROOT)): digest(p) for p in sorted(files)}


def read_rows(path):
    with Path(path).open() as file:
        return list(csv.DictReader(file))


def audit_rows(actual, expected):
    if len(actual) != len(expected):
        raise ValueError('ordered summary count differs')
    largest = 0.0
    for index, (got, wanted) in enumerate(zip(actual, expected)):
        if set(got) != set(wanted):
            raise ValueError('summary schema differs')
        for key in wanted:
            value, reference = float(got[key]), float(wanted[key])
            if key in INTEGER_FIELDS:
                if int(got[key]) != int(wanted[key]):
                    raise ValueError(f'exact field mismatch at {index}/{key}')
            elif not (math.isfinite(value) and math.isfinite(reference) and
                      math.isclose(value, reference, rel_tol=2e-12, abs_tol=1e-9)):
                raise ValueError(f'account mismatch at {index}/{key}: {value} versus {reference}')
            largest = max(largest, abs(value-reference))
    return largest


def validate_config(cfg):
    # A changed plan needs an explicit new file/revision, not command-line scaling.
    expected = dict(kind='synthetic strategy traversal timing pilot', bars=[4096,32768],
                    spans=list(range(2,97,2)), counts=[64,256,1128], seeds=[11,29], repeats=4,
                    capital=1000.0, fee=.0001, maximum_seconds=900,
                    maximum_worker_seconds=30, maximum_evidence_bytes=256*1024**2,
                    maximum_worker_rss_bytes=512*1024**2, maximum_start_load_per_cpu=.5,
                    minimum_free_disk_bytes=1024**3)
    if cfg.get('kind') == 'synthetic strategy traversal main campaign':
        expected.update(kind='synthetic strategy traversal main campaign',seeds=[11,29,47],repeats=8,
                        maximum_quiet_wait_seconds=600,quiet_seconds=60,quiet_sample_seconds=15)
    if any(cfg.get(key) != value for key, value in expected.items()):
        raise ValueError('matrix/budget differs from its frozen configuration')


def plan(cfg, timed):
    rows = []
    for n in cfg['bars']:
        for seed in cfg['seeds']:
            for k in cfg['counts']:
                for repeat in range(cfg['repeats'] if timed else 1):
                    for position, candidate in enumerate(ORDERS[repeat % len(ORDERS)]):
                        order, layout = CANDIDATES[candidate]
                        rows.append(dict(id=f'n{n}-s{seed}-k{k}-r{repeat}-{order}-{layout}',
                                         bars=n, seed=seed, configs=k, repeat=repeat,
                                         order_position=position, order=order, layout=layout))
    return rows


def build_issues(build, timed):
    binary = build/'bin/strategy_replay'
    if not binary.is_file() or not (build/'CMakeCache.txt').is_file():
        return ['missing strategy build']
    cache = (build/'CMakeCache.txt').read_text()
    problems = []
    if timed and ('CMAKE_BUILD_TYPE:STRING=Release\n' not in cache or
                  'MEASURED_SANITIZERS:BOOL=OFF\n' not in cache):
        problems.append('timing requires Release without sanitizers')
    dependencies = [STUDY/'CMakeLists.txt', ROOT/'CMakeLists.txt', *list((STUDY/'src').glob('*'))]
    if any(p.stat().st_mtime_ns > binary.stat().st_mtime_ns for p in dependencies):
        problems.append('build is older than C++ source or CMake; rebuild')
    if not (build/'compile_commands.json').is_file():
        problems.append('missing compile_commands.json')
    return problems


def power_ok(sample):
    power = sample['power']
    text = power.get('stdout', '')
    return power.get('returncode') == 0 and 'AC Power' in text and ('charged' in text or 'charging' in text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--verify', action='store_true')
    mode.add_argument('--pilot', action='store_true')
    mode.add_argument('--main', action='store_true',help='run the frozen confirmation campaign after a quiet entry interval')
    parser.add_argument('--build', type=Path, default=ROOT/'build/release')
    parser.add_argument('--config', type=Path)
    parser.add_argument('--verified', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.config is None:
        args.config = STUDY/'configs'/('main.json' if args.main else 'pilot.json')
    cfg = json.loads(args.config.read_text())
    validate_config(cfg)
    timed = args.pilot or args.main
    if (args.main and cfg['kind'] != 'synthetic strategy traversal main campaign') or (args.pilot and cfg['kind'] != 'synthetic strategy traversal timing pilot'):
        parser.error('execution mode and configuration kind differ')
    build = args.build.resolve()
    binary = build/'bin/strategy_replay'
    entry = environment()
    issues = build_issues(build, timed or args.check)
    load_limit = (entry['cpu_count'] or 1) * cfg['maximum_start_load_per_cpu']
    if timed or args.check:
        if not power_ok(entry):
            issues.append('stable AC power is not established')
        if entry['load_average'][0] > load_limit and not args.main:
            issues.append(f'entry load exceeds {load_limit:g}')
    if args.check:
        print(json.dumps(dict(ready=not issues, issues=issues, environment=entry,
                              planned_observations=len(plan(cfg, True))), indent=2))
        return 0 if not issues else 2
    if args.output is None or (timed and args.verified is None):
        parser.error('--output is required; --pilot also requires --verified')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    sources = source_files()
    binary_hash = digest(binary) if binary.is_file() else None
    manifest = dict(kind=('main measurement' if args.main else 'timing pilot') if timed else 'untimed matrix verification',
                    status='preflight', started_utc=utc(), command=[sys.executable,*sys.argv],
                    cwd=str(Path.cwd()), config=cfg, config_sha256=digest(args.config),
                    git_revision=command(['git','rev-parse','HEAD']),
                    git_state=command(['git','status','--porcelain=v1','--untracked-files=all']),
                    source_sha256=sources, binary_sha256=binary_hash, timed=timed,
                    compiler=command(['g++-16','--version']), python=sys.version,
                    environment=[entry], preflight_issues=issues, datasets=[], executions=[],
                    observations=0, expected_observations=len(plan(cfg,timed)),
                    limitations=['Synthetic bars; no financial-performance inference.',
                                 'CPU affinity, frequency and other processes uncontrolled.',
                                 'No automatic retries or sample deletion.',
                                 'Full trace oracle uses small fixtures; scale gate checks every ordered summary.',
                                 'Source/binary snapshots retained because the working tree may be dirty.'])
    started = time.monotonic()
    locks, observations = [], []

    def save():
        manifest['observations'] = len(observations)
        (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

    def resources():
        size = sum(p.stat().st_size for p in output.rglob('*') if p.is_file())
        elapsed = time.monotonic()-started
        manifest['resources'] = dict(evidence_bytes=size, elapsed_seconds=elapsed)
        if size > cfg['maximum_evidence_bytes'] or elapsed > cfg['maximum_seconds']:
            raise RuntimeError('campaign resource cap reached')

    def execute(argv, label):
        record = dict(id=label, command=list(map(str,argv)), started_utc=utc())
        manifest['executions'].append(record)
        save()
        try:
            result = subprocess.run(record['command'], capture_output=True, text=True,
                                    timeout=min(cfg['maximum_worker_seconds'],
                                                max(.01,cfg['maximum_seconds']-(time.monotonic()-started))))
            (output/(label+'.stdout.json')).write_text(result.stdout)
            (output/(label+'.stderr.txt')).write_text(result.stderr)
            record.update(returncode=result.returncode, stdout_sha256=digest(output/(label+'.stdout.json')))
            result.check_returncode()
            return json.loads(result.stdout)
        except subprocess.TimeoutExpired as error:
            record['error'] = 'worker timeout'
            (output/(label+'.timeout-stdout.txt')).write_bytes(error.stdout or b'')
            (output/(label+'.timeout-stderr.txt')).write_bytes(error.stderr or b'')
            raise
        finally:
            record['finished_utc'] = utc()
            save()

    save()
    try:
        if issues:
            manifest['status'] = 'not_started'
            print('Run held: '+'; '.join(issues), file=sys.stderr)
            return 2
        if shutil.disk_usage(output).free < cfg['minimum_free_disk_bytes']:
            raise RuntimeError('insufficient free disk reserve')
        if timed:
            existing = list((ROOT/'build').glob('*/.main-campaign.lock'))
            if existing or (ROOT/'build/.strategy-campaign.lock').exists():
                raise RuntimeError('another measurement campaign holds a lock')
            for lock in (ROOT/'build/.strategy-campaign.lock', ROOT/'build/barrier-release/.main-campaign.lock',
                         ROOT/'build/precision-release/.main-campaign.lock'):
                lock.parent.mkdir(parents=True,exist_ok=True)
                fd = os.open(lock, os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o600)
                locks.append(lock)
                with os.fdopen(fd,'w') as file:
                    json.dump(dict(pid=os.getpid(),output=str(output)),file)
        with zipfile.ZipFile(output/'source.zip','w',zipfile.ZIP_DEFLATED) as archive:
            for name in sources:
                archive.write(ROOT/name,arcname=name)
        manifest['source_archive_sha256'] = digest(output/'source.zip')
        shutil.copy2(binary, output/'strategy_replay')
        for name in ('CMakeCache.txt','compile_commands.json'):
            shutil.copyfile(build/name, output/name)
        if timed:
            verified = json.loads((args.verified/'manifest.json').read_text())
            if (verified['status'] != 'complete' or verified['timed'] or
                verified['source_sha256'] != sources or verified['binary_sha256'] != binary_hash or
                verified['config_sha256'] != digest(args.config)):
                raise RuntimeError('verification does not match this complete source/build/plan')
            manifest['verification'] = dict(path=str(args.verified.resolve()),
                                            manifest_sha256=digest(args.verified/'manifest.json'))
            for dataset in verified['datasets']:
                for key in ('file','reference'):
                    source = args.verified/dataset[key]
                    if digest(source) != dataset[key+'_sha256']:
                        raise RuntimeError('verified input/reference hash mismatch')
                    shutil.copyfile(source, output/dataset[key])
                manifest['datasets'].append(dataset)
            manifest['timer'] = execute([binary,'--timer'],'timer')
            if not manifest['timer']['steady'] or manifest['timer']['minimum_positive_ns'] <= 0:
                raise RuntimeError('positive steady timer deltas not established')
            manifest['machine'] = command(['sysctl','-n','machdep.cpu.brand_string','hw.memsize','hw.physicalcpu','hw.logicalcpu'])
            manifest['thermal_before'] = command(['pmset','-g','therm'])
            manifest['background_before'] = command(['ps','-Ao','pcpu,comm'])
        else:
            for n in cfg['bars']:
                for seed in cfg['seeds']:
                    bars = synthetic(n, seed)
                    file = output/f'n{n}-s{seed}.csv'
                    write_bars(file,bars)
                    print(f'Independent ledger: N={n}, seed={seed}, K={max(cfg["counts"])}',flush=True)
                    _, summaries, _ = replay(bars,cfg['spans'],max(cfg['counts']),cfg['capital'],cfg['fee'],diagnose=False)
                    reference = output/f'n{n}-s{seed}.reference.csv'
                    with reference.open('w',newline='') as stream:
                        writer=csv.DictWriter(stream,fieldnames=list(summaries[0]),lineterminator='\n')
                        writer.writeheader(); writer.writerows(summaries)
                    manifest['datasets'].append(dict(bars=n,seed=seed,file=file.name,file_sha256=digest(file),
                                                     reference=reference.name,reference_sha256=digest(reference)))
                    resources(); save()
        if args.main:
            manifest['status'] = 'waiting_for_quiet'
            quiet_start = None
            waiting_start = time.monotonic()
            print('Waiting for 60 seconds of low recorded load; at most 10 minutes.',flush=True)
            while time.monotonic()-waiting_start <= cfg['maximum_quiet_wait_seconds']:
                sample = environment(); sample['phase'] = 'quiet_entry'
                manifest['environment'].append(sample)
                if not power_ok(sample):
                    raise RuntimeError('power left stable AC during entry wait')
                now = time.monotonic()
                if sample['load_average'][0] <= load_limit:
                    if quiet_start is None:
                        quiet_start = now
                    if now-quiet_start >= cfg['quiet_seconds']:
                        manifest['measurement_entry_environment'] = sample
                        manifest['quiet_wait_seconds'] = now-waiting_start
                        break
                else:
                    quiet_start = None
                save(); resources()
                time.sleep(cfg['quiet_sample_seconds'])
            else:
                manifest.update(status='not_started',reason='quiet entry interval not established within 10 minutes')
                print(manifest['reason'],flush=True)
                return 2
        executions = plan(cfg,timed)
        for item in executions:
            item['command'] = list(map(str,[binary,'--bars',output/f'n{item["bars"]}-s{item["seed"]}.csv',
                                    '--spans',','.join(map(str,cfg['spans'])), '--count',item['configs'],
                                    '--layout',item['layout'],'--order',item['order'],
                                    '--capital',cfg['capital'],'--fee',cfg['fee'],'--output',output/item['id']]))
            if timed:
                item['command'].append('--time')
        (output/'execution-plan.json').write_text(json.dumps(executions,indent=2)+'\n')
        manifest['execution_plan_sha256'] = digest(output/'execution-plan.json')
        manifest['frozen_before_workers_utc'] = utc()
        manifest['status'] = 'running'; save()
        identities = {}
        group = None
        for item in executions:
            key = (item['bars'],item['seed'],item['configs'])
            if (*key,item['repeat']) != group:
                group = (*key,item['repeat'])
                sample = environment(); manifest['environment'].append(sample)
                if timed and not power_ok(sample):
                    raise RuntimeError('power left stable AC')
                if source_files() != sources or digest(binary) != binary_hash:
                    raise RuntimeError('frozen sources/build changed')
            actual = execute(item['command'],item['id'])
            for field in ('bars','configs','order','layout'):
                if actual.get(field) != item[field]:
                    raise ValueError('worker identity mismatch: '+field)
            if (actual['timed'] != timed or actual['windows'] != len(cfg['spans']) or
                actual['eligible_bars'] != item['bars']-max(cfg['spans'])):
                raise ValueError('worker dimensions/timing differ')
            if actual['peak_rss_bytes'] > cfg['maximum_worker_rss_bytes']:
                raise RuntimeError('worker memory cap exceeded')
            if (actual['whole_ns'] != sum(actual[k+'_ns'] for k in ('feature','layout','setup','replay','summary')) or
                actual['prepared_ns'] != actual['replay_ns']+actual['summary_ns'] or
                (actual['prepared_ns'] <= 0 if timed else actual['whole_ns'] != 0)):
                raise ValueError('invalid timing intervals')
            reference = read_rows(output/f'n{item["bars"]}-s{item["seed"]}.reference.csv')[:item['configs']]
            summary = output/(item['id']+'.summary.csv')
            maximum_error = audit_rows(read_rows(summary),reference)
            fingerprint = digest(summary)
            if key in identities and identities[key] != fingerprint:
                raise ValueError('C++ variants or repetitions differ bit-for-bit')
            identities[key] = fingerprint
            observations.append({k:item[k] for k in ('id','seed','repeat','order_position')} | actual |
                                dict(summary_sha256=fingerprint, maximum_reference_absolute_error=maximum_error))
            (output/'observations.json').write_text(json.dumps(observations,indent=2)+'\n')
            resources(); save()
            if item['order_position'] == 3:
                print(f'Checked {len(observations)}/{len(executions)} workers',flush=True)
        if source_files() != sources or digest(binary) != binary_hash:
            raise RuntimeError('final frozen source/build mismatch')
        for dataset in manifest['datasets']:
            for key in ('file','reference'):
                if digest(output/dataset[key]) != dataset[key+'_sha256']:
                    raise RuntimeError('final dataset integrity mismatch')
        manifest['environment'].append(environment())
        if timed and not power_ok(manifest['environment'][-1]):
            raise RuntimeError('final power state invalid')
        manifest.update(status='complete',final_integrity='passed')
        return 0
    except BaseException as error:
        manifest.update(status='failed',error=repr(error))
        raise
    finally:
        manifest['finished_utc']=utc()
        manifest['elapsed_seconds']=time.monotonic()-started
        save()
        for lock in locks:
            lock.unlink()


if __name__ == '__main__':
    sys.exit(main())
