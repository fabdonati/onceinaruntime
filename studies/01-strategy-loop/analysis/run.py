"""Check account summaries and run the strategy replay benchmarks."""
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
# Each implementation runs once in each slot and follows each other implementation once.
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
    # A benchmark config identifies a specific workload and its limits.
    expected = dict(kind='synthetic strategy traversal timing pilot', bars=[4096,32768],
                    spans=list(range(2,97,2)), counts=[64,256,1128], seeds=[11,29], repeats=4,
                    capital=1000.0, fee=.0001, maximum_seconds=900,
                    maximum_worker_seconds=30, maximum_evidence_bytes=256*1024**2,
                    maximum_worker_rss_bytes=512*1024**2, maximum_start_load_per_cpu=.5,
                    minimum_free_disk_bytes=1024**3)
    if cfg.get('kind') == 'synthetic strategy traversal main campaign':
        expected.update(kind='synthetic strategy traversal main campaign',seeds=[11,29,47],repeats=8,
                        maximum_quiet_wait_seconds=600,quiet_seconds=60,quiet_sample_seconds=15)
    if cfg.get('input_kind') == 'historical':
        expected.pop('seeds')
        expected.update(kind='historical strategy traversal main campaign', input_kind='historical',
                        schema_version=1, counts=[64,1128], repeats=8,
                        profiles=['jump','directional','low-directionality'],
                        maximum_quiet_wait_seconds=600,quiet_seconds=60,quiet_sample_seconds=15)
        if cfg.get('kind') == 'historical strategy traversal timing pilot':
            expected.update(kind=cfg['kind'], bars=[32768], counts=[1128], repeats=4)
        if len(cfg.get('input_manifest_sha256','')) != 64:
            raise ValueError('historical input manifest hash is required')
    if any(cfg.get(key) != value for key, value in expected.items()):
        raise ValueError('matrix/budget differs from its frozen configuration')


def plan(cfg, timed):
    rows = []
    if cfg.get('input_kind') == 'historical':
        blocks = [(p,n,k) for p in cfg['profiles'] for n in cfg['bars'] for k in cfg['counts']]
        for repeat in range(cfg['repeats'] if timed else 1):
            rotation = repeat % len(blocks)
            for profile,n,k in blocks[rotation:]+blocks[:rotation]:
                dataset_id = f'qqq-{profile}-n{n}'
                for position,candidate in enumerate(ORDERS[repeat % len(ORDERS)]):
                    order,layout = CANDIDATES[candidate]
                    rows.append(dict(id=f'{dataset_id}-k{k}-r{repeat}-{order}-{layout}',
                        input_kind='historical', schema_version=1, dataset_id=dataset_id,
                        input_manifest_sha256=cfg['input_manifest_sha256'], profile=profile,
                        bars=n,configs=k,repeat=repeat,order_position=position,order=order,layout=layout))
        return rows
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


def power_ok(sample, allow_battery=False):
    power = sample['power']
    text = power.get('stdout', '')
    if power.get('returncode') != 0:
        return False
    ac = 'AC Power' in text and any(state in text for state in ('charged', 'charging', 'finishing charge'))
    battery = 'Battery Power' in text and 'discharging' in text
    return ac or (allow_battery and battery)


def power_mode(sample):
    return 'battery' if 'Battery Power' in sample['power'].get('stdout','') else 'AC'


def dataset_id(item):
    return item.get('dataset_id') or f'n{item["bars"]}-s{item["seed"]}'


def verification_matches(verified, cfg, sources, binary_hash, config_hash):
    if (verified.get('status') != 'complete' or verified.get('final_integrity') != 'passed' or
        verified.get('timed') or verified['source_sha256'] != sources or
        verified['binary_sha256'] != binary_hash):
        return False
    if cfg.get('input_kind') != 'historical':
        return verified['config_sha256'] == config_hash
    # The historical pilot uses a subset of the cases checked for the main run.
    prior = verified['config']
    try:
        validate_config(prior)
    except ValueError:
        return False
    if (prior.get('kind') != 'historical strategy traversal main campaign' or
        prior.get('input_manifest_sha256') != cfg['input_manifest_sha256'] or
        verified['observations'] != len(plan(prior,False))):
        return False
    for field in ('spans','capital','fee','profiles'):
        if prior[field] != cfg[field]:
            return False
    return set(cfg['bars']) <= set(prior['bars']) and set(cfg['counts']) <= set(prior['counts'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--verify', action='store_true')
    mode.add_argument('--pilot', action='store_true')
    mode.add_argument('--main', action='store_true', help='run the main benchmark after the load check')
    parser.add_argument('--build', type=Path, default=ROOT/'build/release')
    parser.add_argument('--config', type=Path)
    parser.add_argument('--verified', type=Path)
    parser.add_argument('--datasets', type=Path, help='historical input manifest for verification')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--allow-battery', action='store_true',
                        help='explicitly permit recorded battery operation; distinguish results from AC campaigns')
    args = parser.parse_args()
    if args.config is None:
        args.config = STUDY/'configs'/('main.json' if args.main else 'pilot.json')
    cfg = json.loads(args.config.read_text())
    validate_config(cfg)
    timed = args.pilot or args.main
    historical = cfg.get('input_kind') == 'historical'
    prefix = 'historical' if historical else 'synthetic'
    if (args.main and cfg['kind'] != prefix+' strategy traversal main campaign') or (args.pilot and cfg['kind'] != prefix+' strategy traversal timing pilot'):
        parser.error('execution mode and configuration kind differ')
    build = args.build.resolve()
    binary = build/'bin/strategy_replay'
    entry = environment()
    issues = build_issues(build, timed or args.check)
    load_limit = (entry['cpu_count'] or 1) * cfg['maximum_start_load_per_cpu']
    if timed or args.check:
        if not power_ok(entry, args.allow_battery):
            issues.append('accepted power state is not established' if args.allow_battery
                          else 'stable AC power is not established')
        if entry['load_average'][0] > load_limit and not (args.main or historical):
            issues.append(f'entry load exceeds {load_limit:g}')
    if args.check:
        print(json.dumps(dict(ready=not issues, issues=issues, environment=entry,
                              planned_observations=len(plan(cfg, True))), indent=2))
        return 0 if not issues else 2
    if args.output is None or (timed and args.verified is None):
        parser.error('set --output for verification and timing, and --verified for timing')
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
                    power_policy=('AC or battery explicitly permitted' if args.allow_battery else 'stable AC required'),
                    allow_battery=args.allow_battery,
                    observations=0, expected_observations=len(plan(cfg,timed)),
                    limitations=['Synthetic bars; no financial-performance inference.',
                                 'CPU affinity, frequency and other processes uncontrolled.',
                                 'No automatic retries or sample deletion.',
                                 'Full trace oracle uses small fixtures; scale gate checks every ordered summary.',
                                 'Source/binary snapshots retained because the working tree may be dirty.'])
    if args.allow_battery:
        manifest['limitations'].append('Battery operation explicitly permitted; do not pool with AC timings as identical conditions.')
    if historical:
        manifest.update(input_kind='historical',schema_version=1,
                        input_manifest_sha256=cfg['input_manifest_sha256'],power_condition=power_mode(entry))
        manifest['limitations'][0] = 'Selected QQQ minute bars; simplified price-only accounts, not executable trading performance.'
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
            if not verification_matches(verified,cfg,sources,binary_hash,digest(args.config)):
                raise RuntimeError('verification does not match this complete source/build/plan')
            manifest['verification'] = dict(path=str(args.verified.resolve()),
                                            manifest_sha256=digest(args.verified/'manifest.json'))
            if historical:
                if digest(args.verified/'input-manifest.json') != cfg['input_manifest_sha256']:
                    raise RuntimeError('historical input manifest changed')
                shutil.copyfile(args.verified/'input-manifest.json',output/'input-manifest.json')
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
            if historical:
                if args.datasets is None or digest(args.datasets) != cfg['input_manifest_sha256']:
                    raise RuntimeError('historical manifest missing or hash differs')
                inputs = json.loads(args.datasets.read_text())
                if inputs['status'] != 'complete' or inputs['input_kind'] != 'historical':
                    raise RuntimeError('historical dataset is incomplete')
                items = inputs['datasets']
                wanted = {f'qqq-{p}-n{n}' for p in cfg['profiles'] for n in cfg['bars']}
                if len(items) != len(wanted) or {dataset_id(d) for d in items} != wanted:
                    raise RuntimeError('historical datasets differ from frozen matrix')
                shutil.copyfile(args.datasets,output/'input-manifest.json')
            else:
                items = [dict(bars=n,seed=seed) for n in cfg['bars'] for seed in cfg['seeds']]
            for item in items:
                    n = item['bars']
                    if historical:
                        source = args.datasets.parent/item['file']
                        if digest(source) != item['file_sha256']:
                            raise RuntimeError('historical CSV hash differs')
                        bars = [(int(r['timestamp']),float(r['open']),float(r['close'])) for r in read_rows(source)]
                        if len(bars) != n:
                            raise RuntimeError('historical row count differs')
                    else:
                        bars = synthetic(n, item['seed'])
                    file = output/(dataset_id(item)+'.csv')
                    write_bars(file,bars)
                    if historical and digest(file) != item['file_sha256']:
                        raise RuntimeError('canonical historical bytes differ')
                    print(f'Independent ledger: {dataset_id(item)}, K={max(cfg["counts"])}',flush=True)
                    _, summaries, _ = replay(bars,cfg['spans'],max(cfg['counts']),cfg['capital'],cfg['fee'],diagnose=False)
                    reference = output/(dataset_id(item)+'.reference.csv')
                    with reference.open('w',newline='') as stream:
                        writer=csv.DictWriter(stream,fieldnames=list(summaries[0]),lineterminator='\n')
                        writer.writeheader(); writer.writerows(summaries)
                    manifest['datasets'].append(dict(item, file=file.name,file_sha256=digest(file),
                                                     reference=reference.name,reference_sha256=digest(reference)))
                    resources(); save()
        if args.main or (historical and timed):
            manifest['status'] = 'waiting_for_quiet'
            quiet_start = None
            waiting_start = time.monotonic()
            print('Waiting for 60 seconds of low recorded load; at most 10 minutes.',flush=True)
            while time.monotonic()-waiting_start <= cfg['maximum_quiet_wait_seconds']:
                sample = environment(); sample['phase'] = 'quiet_entry'
                manifest['environment'].append(sample)
                if not power_ok(sample, args.allow_battery):
                    raise RuntimeError('power left accepted state during entry wait')
                if historical and power_mode(sample) != manifest['power_condition']:
                    raise RuntimeError('historical power condition changed')
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
            item['command'] = list(map(str,[binary,'--bars',output/(dataset_id(item)+'.csv'),
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
            key = (dataset_id(item),item['configs'])
            if (*key,item['repeat']) != group:
                group = (*key,item['repeat'])
                sample = environment(); manifest['environment'].append(sample)
                if timed and not power_ok(sample, args.allow_battery):
                    raise RuntimeError('power left accepted state')
                if timed and historical and power_mode(sample) != manifest['power_condition']:
                    raise RuntimeError('historical power condition changed')
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
            reference = read_rows(output/(dataset_id(item)+'.reference.csv'))[:item['configs']]
            summary = output/(item['id']+'.summary.csv')
            maximum_error = audit_rows(read_rows(summary),reference)
            fingerprint = digest(summary)
            if key in identities and identities[key] != fingerprint:
                raise ValueError('C++ variants or repetitions differ bit-for-bit')
            identities[key] = fingerprint
            identity_fields = ('input_kind','schema_version','dataset_id','profile','input_manifest_sha256') if historical else ('seed',)
            observations.append({k:item[k] for k in ('id','repeat','order_position',*identity_fields)} | actual |
                                dict(summary_sha256=fingerprint, maximum_reference_absolute_error=maximum_error))
            if historical:
                observations[-1]['power_condition'] = manifest['power_condition']
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
        if timed and not power_ok(manifest['environment'][-1], args.allow_battery):
            raise RuntimeError('final power state invalid')
        if timed and historical and power_mode(manifest['environment'][-1]) != manifest['power_condition']:
            raise RuntimeError('final historical power condition changed')
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
