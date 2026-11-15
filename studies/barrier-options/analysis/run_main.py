"""One bounded main campaign, with balanced order and audited temporary outputs."""
import argparse
import datetime as dt
import gc
import itertools
import json
import math
import os
from pathlib import Path
import platform
import resource
import shutil
import subprocess
import sys
import time
import zipfile

import numpy as np
from model import DISCOUNT, generate, oracle, vanilla_diagnostic
from run_pilot import ROOT, HERE, command, digest, source_files
from verify import audit_output

GIB = 1024 ** 3
PERMUTATIONS = tuple(itertools.permutations(('scalar', 'fixed', 'refill')))


class StartConditionError(RuntimeError):
    pass


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def validate_config(cfg):
    expected = {'kind': 'bounded main campaign', 'paths': 100000, 'steps': 252,
                'seeds': [11, 29, 47], 'barriers': [105, 120, 150],
                'layouts': ['path', 'step'], 'methods': ['scalar', 'fixed', 'refill'],
                'process_repeats_per_seed_case': 6, 'prepared_warmups': 1,
                'complete_valuation_warmups': 1, 'maximum_seconds': 1800,
                'maximum_evidence_bytes': GIB, 'maximum_combined_peak_rss_bytes': GIB,
                'maximum_start_load_per_cpu': 0.5}
    if any(cfg.get(k) != v for k, v in expected.items()):
        raise ValueError('configuration differs from the bounded main-campaign agreement')


def power_is_stable(record):
    text = record.get('stdout', '').lower()
    return (record.get('returncode') == 0 and "'ac power'" in text
            and 'discharging' not in text
            and any(word in text for word in ('charging', 'charged', 'finishing charge')))


def environment(label):
    power = command(['pmset', '-g', 'batt']) if sys.platform == 'darwin' else {'error': 'AC state unavailable'}
    return {'label': label, 'utc': utc(), 'load_average': list(os.getloadavg()),
            'cpu_count': os.cpu_count(), 'power': power}


def require_power(sample):
    if not power_is_stable(sample['power']):
        raise StartConditionError('stable AC power required: ' + sample['power'].get('stdout', str(sample['power'])).strip())


def build_issues(build):
    issues = []
    try:
        cache = (build / 'CMakeCache.txt').read_text()
    except OSError:
        return ['release build cache is missing or unreadable']
    for setting in ('CMAKE_BUILD_TYPE:STRING=Release\n', 'MEASURED_SANITIZERS:BOOL=OFF\n', 'OIR_BARRIER_SIMD:BOOL=ON\n'):
        if setting not in cache:
            issues.append('release build setting missing: ' + setting.strip())
    library = build / 'lib' / ('libbarrier_core.dylib' if sys.platform == 'darwin' else 'libbarrier_core.so')
    for path in (build / 'bin/barrier_bench', library, build / 'compile_commands.json'):
        if not path.is_file():
            issues.append('release artifact is missing: ' + str(path))
    return issues


def estimates(cfg):
    array_bytes = cfg['paths'] * cfg['steps'] * 8
    reference_bytes = len(cfg['seeds']) * len(cfg['barriers']) * cfg['paths'] * 17
    return {'canonical_array_bytes': array_bytes,
            'retained_canonical_bytes': len(cfg['seeds']) * array_bytes,
            'reference_bytes': reference_bytes,
            'estimated_peak_evidence_bytes': (len(cfg['seeds']) + 1) * array_bytes + reference_bytes + 32 * 1024 ** 2,
            'estimated_combined_peak_rss_bytes': 4 * array_bytes + 128 * 1024 ** 2}


def plan(cfg):
    result = []
    cases = list(itertools.product(cfg['barriers'], cfg['layouts']))
    for si, seed in enumerate(cfg['seeds']):
        for ci, (barrier, layout) in enumerate(cases):
            offset = (si + ci) % len(PERMUTATIONS)
            orders = PERMUTATIONS[offset:] + PERMUTATIONS[:offset]
            for repeat, order in enumerate(orders[:cfg['process_repeats_per_seed_case']]):
                for position, method in enumerate(order):
                    result.append({'id': f's{seed}-b{barrier}-{layout}-r{repeat}-{method}',
                                   'seed': seed, 'barrier': barrier, 'layout': layout,
                                   'repeat': repeat, 'order_position': position, 'method': method})
    return result


def step_major(canonical, output, paths, steps):
    if canonical.stat().st_size != paths * steps * 8:
        raise ValueError('canonical dimensions disagree with byte count')
    original = np.memmap(canonical, dtype='<f8', mode='r', shape=(paths, steps))
    derived = np.ascontiguousarray(original.T)
    derived.tofile(output)
    result = {'sha256': digest(output), 'bytes': output.stat().st_size}
    del derived, original
    gc.collect()
    return result


def rss_peaks():
    unit = 1 if sys.platform == 'darwin' else 1024
    parent = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * unit
    child = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss * unit
    return {'parent_peak_bytes': parent, 'maximum_reaped_child_peak_bytes': child,
            'conservative_combined_peak_bytes': parent + child}


def check_complete(result, item, cfg, canonical_hash, layout_hash, payoff_hash):
    for key in ('seed', 'barrier', 'layout', 'method'):
        if result.get(key) != item[key]:
            raise RuntimeError('whole observation identity mismatch: ' + key)
    if result.get('paths') != cfg['paths'] or result.get('steps') != cfg['steps'] or not result.get('validated'):
        raise RuntimeError('whole observation dimensions/validation mismatch')
    keys = ('generation_ns', 'layout_ns', 'output_allocation_bridge_compute_ns')
    if any(not isinstance(result.get(k), int) or result[k] < 0 for k in (*keys, 'complete_ns')):
        raise RuntimeError('invalid whole phase duration')
    if result['complete_ns'] <= 0 or sum(result[k] for k in keys) != result['complete_ns']:
        raise RuntimeError('whole phase sum mismatch')
    for key, expected in (('canonical_sha256', canonical_hash), ('layout_sha256', layout_hash), ('payoffs_sha256', payoff_hash)):
        if result.get(key) != expected:
            raise RuntimeError('whole observation checksum mismatch: ' + key)
    if not math.isfinite(result.get('price', math.nan)):
        raise RuntimeError('nonfinite whole price')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, default=ROOT / 'build/barrier-release')
    parser.add_argument('--config', type=Path, default=HERE.parent / 'configs/main.json')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--check', action='store_true', help='read-only preflight; no data generation or timings')
    parser.add_argument('--smoke', action='store_true', help='257 paths, 17 steps, one seed/barrier/repeat; harness check only')
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text())
    validate_config(cfg)
    if args.smoke:
        cfg = cfg | {'kind': 'main-runner functional smoke, not main evidence', 'paths': 257,
                     'steps': 17, 'seeds': [11], 'barriers': [120],
                     'process_repeats_per_seed_case': 1, 'maximum_seconds': 60}
    estimate = estimates(cfg)
    start_sample = environment('preflight')
    cpu_count = start_sample['cpu_count'] or 1
    start_load_limit = cpu_count * cfg['maximum_start_load_per_cpu']
    build = args.build.resolve()
    issues = build_issues(build)
    if not power_is_stable(start_sample['power']):
        issues.append('battery is not reporting stable AC charging/charged')
    if start_sample['load_average'][0] > start_load_limit:
        issues.append(f'one-minute load exceeds the declared start gate of {start_load_limit:g}')
    if estimate['estimated_peak_evidence_bytes'] >= cfg['maximum_evidence_bytes']:
        issues.append('estimated evidence exceeds budget')
    if estimate['estimated_combined_peak_rss_bytes'] >= cfg['maximum_combined_peak_rss_bytes']:
        issues.append('estimated combined process memory exceeds budget')
    if shutil.disk_usage(ROOT).free < estimate['estimated_peak_evidence_bytes'] + GIB:
        issues.append('insufficient disk space with 1 GiB reserve')
    if args.check:
        print(json.dumps({'ready': not issues, 'issues': issues, 'environment': start_sample,
                          'start_load_limit': start_load_limit, 'estimates': estimate}, indent=2))
        return 0 if not issues else 2
    if not args.output:
        parser.error('--output is required unless --check is used')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    scratch = output / 'temporary'
    scratch.mkdir()
    binary = build / 'bin/barrier_bench'
    library = build / 'lib' / ('libbarrier_core.dylib' if sys.platform == 'darwin' else 'libbarrier_core.so')
    expected_plan = plan(cfg)
    source_before = source_files()
    manifest = {'status': 'preflight', 'started_utc': utc(), 'command': [sys.executable, *sys.argv],
                'cwd': str(Path.cwd()), 'config': cfg, 'original_config_sha256': digest(args.config),
                'source_sha256': source_before,
                'binary_sha256': digest(binary) if binary.is_file() else None,
                'library_sha256': digest(library) if library.is_file() else None,
                'git_revision': command(['git', 'rev-parse', 'HEAD']),
                'git_state': command(['git', 'status', '--porcelain=v1', '--untracked-files=all']),
                'compiler': command(['g++-16', '--version']), 'python': sys.version,
                'numpy': np.__version__, 'platform': platform.platform(), 'estimates': estimate,
                'start_load_limit': start_load_limit, 'preflight_issues': issues, 'environment': [start_sample],
                'datasets': [], 'references': [], 'executions': [], 'observation_count': 0,
                'expected_observations': len(expected_plan), 'pricing_processes': 0,
                'retention': 'Keep canonical arrays, oracle outputs, per-process metadata/hashes. Delete derived layout/output bytes only after successful auditing.',
                'limits': ['One thread; no affinity/frequency/core/thermal control.',
                           'Prepared and whole scopes use separate sequential fresh processes.',
                           'No samples excluded/replaced; no additional repetitions after inspecting results.',
                           'Whole scope includes NumPy generation and ctypes; excludes imports, validation, serialization and destruction.',
                           'Load gates only entry to observations. Later load changes are retained, not sample filters.',
                           'Memory check sums parent/child peak RSS as a conservative bound; peaks need not coincide.']}
    observations = []
    clock_start = time.monotonic()
    lock = build / '.main-campaign.lock'
    locked = False

    def save():
        manifest['observation_count'] = len(observations)
        (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')

    def resources():
        if time.monotonic() - clock_start >= cfg['maximum_seconds']:
            raise RuntimeError('campaign wall-time cap reached')
        size = sum(p.stat().st_size for p in output.rglob('*') if p.is_file())
        peaks = rss_peaks()
        manifest['latest_resources'] = peaks | {'evidence_bytes': size, 'elapsed_seconds': time.monotonic() - clock_start}
        if size >= cfg['maximum_evidence_bytes']:
            raise RuntimeError('evidence disk cap reached')
        if peaks['conservative_combined_peak_bytes'] >= cfg['maximum_combined_peak_rss_bytes']:
            raise RuntimeError('conservative combined peak-RSS cap reached')

    def sample(label, check_start_load=False):
        record = environment(label)
        manifest['environment'].append(record)
        save()
        require_power(record)
        if check_start_load and record['load_average'][0] > start_load_limit:
            raise StartConditionError('observation entry load exceeds declared start gate')
        resources()

    def run(cmd, label, pricing=False):
        resources()
        record = {'id': label, 'command': list(map(str, cmd)), 'started_utc': utc(),
                  'stdout': label + '.stdout.json', 'stderr': label + '.stderr.txt',
                  'pricing_worker': pricing}
        manifest['executions'].append(record)
        save()
        remaining = cfg['maximum_seconds'] - (time.monotonic() - clock_start)
        process = None
        stdout = stderr = ''
        try:
            process = subprocess.Popen(record['command'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            record['pid'] = process.pid
            if pricing:
                manifest['pricing_processes'] += 1
            try:
                stdout, stderr = process.communicate(timeout=max(.01, min(60, remaining)))
            except subprocess.TimeoutExpired:
                process.kill()  # Only this campaign's own timed-out child.
                stdout, stderr = process.communicate()
                record['timed_out'] = True
                raise RuntimeError('worker or campaign time cap reached')
            record['returncode'] = process.returncode
            if process.returncode:
                raise RuntimeError(f'{label}: worker exit {process.returncode}')
            result = json.loads(stdout)
            resources()
            return result, record
        except BaseException as error:
            if process is not None and process.poll() is None:
                process.kill()
                stdout, stderr = process.communicate()
            record['error'] = repr(error)
            raise
        finally:
            (output / record['stdout']).write_text(stdout)
            (output / record['stderr']).write_text(stderr)
            record['finished_utc'] = utc()
            record['stdout_sha256'] = digest(output / record['stdout'])
            record['stderr_sha256'] = digest(output / record['stderr'])
            save()

    def retire(paths, record):
        record['audited_outputs'] = []
        for path in paths:
            record['audited_outputs'].append({'name': str(path.relative_to(output)),
                                             'bytes': path.stat().st_size, 'sha256': digest(path)})
        save()  # Retain the audit record before removing redundant byte copies.
        for path in paths:
            path.unlink()
        record['output_bytes_removed_after_audit'] = True
        save()

    save()
    try:
        if issues:
            raise StartConditionError('; '.join(issues))
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        locked = True
        with os.fdopen(fd, 'w') as f:
            json.dump({'pid': os.getpid(), 'output': str(output), 'started_utc': utc()}, f)
        with zipfile.ZipFile(output / 'source.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for name in source_before:
                archive.write(ROOT / name, arcname=name)
        manifest['source_archive_sha256'] = digest(output / 'source.zip')
        for name in ('CMakeCache.txt', 'compile_commands.json'):
            shutil.copyfile(build / name, output / name)
        manifest['background_before'] = command(['ps', '-Ao', 'pcpu,comm'])
        manifest['thermal_before'] = command(['pmset', '-g', 'therm'])
        manifest['memory_before'] = command(['vm_stat'])
        manifest['cpp_timer'], _ = run([binary, '--timer'], 'timer')
        deltas = []
        previous = time.perf_counter_ns()
        for _ in range(10000):
            now = time.perf_counter_ns(); deltas.append(now - previous); previous = now
        manifest['python_clock'] = {'info': str(time.get_clock_info('perf_counter')), 'deltas_ns': deltas}

        for seed in cfg['seeds']:
            sample(f'before preparing seed {seed}')
            factors = generate(cfg['paths'], cfg['steps'], seed)
            canonical = output / f'seed-{seed}-path.f64'
            factors.tofile(canonical)
            manifest['datasets'].append({'seed': seed, 'paths': cfg['paths'], 'steps': cfg['steps'],
                                         'canonical': {'name': canonical.name, 'bytes': canonical.stat().st_size, 'sha256': digest(canonical)},
                                         'vanilla': vanilla_diagnostic(factors)})
            for barrier in cfg['barriers']:
                reference = oracle(factors, barrier)
                files = {}
                for suffix, values in zip(('payoffs.f64', 'lifetimes.u64', 'knocked.u8'), reference):
                    path = output / f'ref-{seed}-{barrier}.{suffix}'
                    values.tofile(path)
                    files[suffix] = {'name': path.name, 'bytes': path.stat().st_size, 'sha256': digest(path)}
                manifest['references'].append({'seed': seed, 'barrier': barrier, 'files': files})
                del reference, values
            del factors
            gc.collect()
            save(); resources()

        # Freeze exact policy order and both commands for every observation before any timing.
        for item in expected_plan:
            prefix = scratch / item['id']
            input_path = output / f"seed-{item['seed']}-path.f64" if item['layout'] == 'path' else scratch / f"seed-{item['seed']}-step.f64"
            item['prepared_command'] = list(map(str, [binary, input_path, cfg['paths'], cfg['steps'], item['layout'], item['method'], item['barrier'], DISCOUNT, prefix, '--time']))
            item['complete_command'] = list(map(str, [sys.executable, HERE / 'valuation.py', '--library', library,
                            '--canonical', output / f"seed-{item['seed']}-path.f64", '--reference', output / f"ref-{item['seed']}-{item['barrier']}.payoffs.f64",
                            '--output', scratch / (item['id'] + '-complete.payoffs.f64'), '--paths', cfg['paths'], '--steps', cfg['steps'],
                            '--seed', item['seed'], '--barrier', item['barrier'], '--layout', item['layout'], '--method', item['method']]))
        (output / 'execution-plan.json').write_text(json.dumps(expected_plan, indent=2) + '\n')
        manifest['execution_plan_sha256'] = digest(output / 'execution-plan.json')
        manifest['frozen_before_observations_utc'] = utc()
        sample('before observations', check_start_load=True)
        manifest['status'] = 'running'
        save()
        previous_group = None
        current_seed = None
        derived = None
        for item in expected_plan:
            group = (item['seed'], item['barrier'], item['layout'], item['repeat'])
            if group != previous_group:
                sample(f'before seed/barrier/layout/repeat {group}')
                if source_files() != source_before or digest(binary) != manifest['binary_sha256'] or digest(library) != manifest['library_sha256']:
                    raise RuntimeError('frozen source/executable changed during campaign')
                previous_group = group
            if item['seed'] != current_seed:
                if derived is not None:
                    if digest(derived) != dataset['derived']['sha256']:
                        raise RuntimeError('temporary step-major input changed')
                    derived.unlink()
                current_seed = item['seed']
                derived = None
                dataset = next(d for d in manifest['datasets'] if d['seed'] == current_seed)
            if item['layout'] == 'step' and derived is None:
                derived = scratch / f'seed-{current_seed}-step.f64'
                metadata = step_major(output / dataset['canonical']['name'], derived, cfg['paths'], cfg['steps'])
                dataset['derived'] = metadata | {'name': str(derived.relative_to(output)), 'retained': False}
                save(); resources()
            reference_info = next(r for r in manifest['references'] if (r['seed'], r['barrier']) == (item['seed'], item['barrier']))
            reference = tuple(np.fromfile(output / reference_info['files'][suffix]['name'], dtype=dtype)
                              for suffix, dtype in (('payoffs.f64', '<f8'), ('lifetimes.u64', '<u8'), ('knocked.u8', 'u1')))
            prepared, prepared_record = run(item['prepared_command'], item['id'] + '-prepared', pricing=True)
            for key in ('paths', 'steps'):
                if prepared.get(key) != cfg[key]:
                    raise RuntimeError('prepared dimensions mismatch')
            for key in ('layout', 'method', 'barrier'):
                if prepared.get(key) != item[key]:
                    raise RuntimeError('prepared identity mismatch')
            if (not prepared.get('validated_cpp') or not prepared.get('timed')
                    or not isinstance(prepared.get('prepared_ns'), int) or prepared['prepared_ns'] <= 0
                    or not math.isfinite(prepared['price'])):
                raise RuntimeError('invalid prepared observation')
            prefix = scratch / item['id']
            audit_output(prefix, reference)
            prepared_record['independent_payoff_date_knockout_audit'] = True
            retire([Path(str(prefix) + '.' + suffix) for suffix in ('payoffs.f64', 'lifetimes.u64', 'knocked.u8')], prepared_record)
            whole, whole_record = run(item['complete_command'], item['id'] + '-complete', pricing=True)
            check_complete(whole, item, cfg, dataset['canonical']['sha256'],
                           dataset['canonical']['sha256'] if item['layout'] == 'path' else dataset['derived']['sha256'],
                           reference_info['files']['payoffs.f64']['sha256'])
            whole_output = scratch / (item['id'] + '-complete.payoffs.f64')
            if not np.array_equal(np.fromfile(whole_output, dtype='<f8'), reference[0]) or whole['price'] != prepared['price']:
                raise RuntimeError('independent whole output/aggregate mismatch')
            whole_record['independent_payoff_audit'] = True
            retire([whole_output], whole_record)
            observations.append({k: item[k] for k in ('id', 'seed', 'repeat', 'order_position')} | prepared | {'complete': whole})
            (output / 'observations.json').write_text(json.dumps(observations, indent=2) + '\n')
            del reference
            save()
            if item['order_position'] == 2:
                print(f"Saved {len(observations)}/{len(expected_plan)}: seed {item['seed']}, barrier {item['barrier']}, {item['layout']}, repeat {item['repeat']}", flush=True)
        if derived is not None:
            if digest(derived) != dataset['derived']['sha256']:
                raise RuntimeError('last temporary input changed')
            derived.unlink()
        sample('after observations')
        for dataset in manifest['datasets']:
            if digest(output / dataset['canonical']['name']) != dataset['canonical']['sha256']:
                raise RuntimeError('canonical input changed')
        for reference_info in manifest['references']:
            for metadata in reference_info['files'].values():
                if digest(output / metadata['name']) != metadata['sha256']:
                    raise RuntimeError('retained oracle output changed')
        if source_files() != source_before or digest(binary) != manifest['binary_sha256'] or digest(library) != manifest['library_sha256']:
            raise RuntimeError('frozen code/executable changed')
        if len(observations) != len(expected_plan) or manifest['pricing_processes'] != 2 * len(expected_plan):
            raise RuntimeError('incomplete observation matrix')
        manifest['status'] = 'complete'
        manifest['final_integrity_checks'] = 'canonical inputs, references, sources, binaries and planned process count passed'
        resources()
        print('Complete: all observations retained and audited; no main-campaign interpretation added.', flush=True)
        return 0
    except StartConditionError as error:
        manifest.update(status='not_started' if not observations else 'stopped', error=str(error))
        print('Campaign held: ' + str(error), file=sys.stderr)
        return 2
    except BaseException as error:
        manifest.update(status='failed', error=repr(error))
        raise
    finally:
        manifest['finished_utc'] = utc()
        manifest['elapsed_seconds'] = time.monotonic() - clock_start
        save()
        if locked:
            lock.unlink()


if __name__ == '__main__':
    raise SystemExit(main())
