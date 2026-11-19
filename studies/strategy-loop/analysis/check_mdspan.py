"""Bounded access comparison: one frozen workload, eight checks, optional pilot.

This does not replace the historical traversal/layout campaign. Timings are a
four-pair pilot per traversal/layout, not a statistical equivalence test.
"""
import argparse
from collections import Counter
import difflib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import zipfile

from run import (ROOT, CANDIDATES, ORDERS, audit_rows, command, digest, environment,
                 power_mode, power_ok, read_rows, source_files, utc)


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def replay_instructions(text):
    """Extract the complete non-diagnostic replay from llvm-objdump output."""
    active = False
    instructions = []
    for line in text.splitlines():
        header = re.match(r'^[0-9a-f]+ <(.+)>:$', line)
        if header:
            active = header[1].startswith('strategy::replay(')
        match = re.match(r'^\s+([0-9a-f]+):\s+([0-9a-f]{8})\s+(.+)$', line)
        if active and match:
            instructions.append(dict(address=match[1], encoding=match[2], assembly=match[3]))
    if not instructions:
        raise ValueError('no replay instructions decoded; inspect disassembler format')
    return instructions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, default=ROOT/'build/release')
    parser.add_argument('--verified', type=Path, required=True,
                        help='retained historical verification directory')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pilot', action='store_true')
    parser.add_argument('--allow-battery', action='store_true')
    args = parser.parse_args()
    build, verified, out = (p.resolve() for p in (args.build, args.verified, args.output))
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    sources = source_files()
    manifest = dict(status='started', started_utc=utc(), command=sys.argv,
                    cwd=str(Path.cwd()), source_sha256=sources,
                    revision=command(['git', 'rev-parse', 'HEAD']),
                    dirty_state=command(['git', 'status', '--short']),
                    environment=[], observations=[], executions=[],
                    limits=dict(seconds=900, worker_seconds=30, quiet_wait_seconds=600,
                                evidence_bytes=268435456, worker_rss_bytes=536870912),
                    workload=dict(profile='directional', bars=32768, windows=48,
                                  configs=1128, warmup=96, capital=1000.0, fee=.0001),
                    pilot_repeats=4 if args.pilot else 0,
                    interpretation='Untimed output gate, then optional descriptive paired pilot; no equivalence margin or production latency claim.')
    locks = []

    def checkpoint():
        save(out/'manifest.json', manifest)
        if time.monotonic()-started > 900:
            raise RuntimeError('900-second cap reached')
        if sum(p.stat().st_size for p in out.rglob('*') if p.is_file()) > 268435456:
            raise RuntimeError('256 MiB evidence cap reached')

    try:
        checkpoint()
        if shutil.disk_usage(out).free < 1073741824:
            raise RuntimeError('less than 1 GiB disk reserve')
        retained = json.loads((verified/'manifest.json').read_text())
        if retained['status'] != 'complete' or retained['timed']:
            raise ValueError('need a completed untimed reference gate')
        if retained['config']['spans'] != list(range(2, 97, 2)) or any(
                retained['config'][k] != manifest['workload'][k] for k in ('capital', 'fee')):
            raise ValueError('reference accounting contract differs')
        dataset, = [d for d in retained['datasets'] if d['dataset_id'] == 'qqq-directional-n32768']
        manifest['reference_manifest_sha256'] = digest(verified/'manifest.json')
        manifest['dataset'] = dataset
        for key in ('file', 'reference'):
            if digest(verified/dataset[key]) != dataset[key+'_sha256']:
                raise ValueError('retained input/reference hash mismatch')
            shutil.copy2(verified/dataset[key], out/dataset[key])
        expected = read_rows(out/dataset['reference'])
        if len(expected) != 1128:
            raise ValueError('unexpected reference size')
        if 'CMAKE_BUILD_TYPE:STRING=Release' not in (build/'CMakeCache.txt').read_text():
            raise ValueError('release build required')
        for name in ('CMakeCache.txt', 'compile_commands.json'):
            shutil.copy2(build/name, out/name)
        with zipfile.ZipFile(out/'source.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for name in sources:
                archive.write(ROOT/name, name)
        manifest['source_archive_sha256'] = digest(out/'source.zip')
        manifest['tools'] = [command(['g++-16', '--version']), command(['xcrun', 'llvm-objdump', '--version']),
                             command(['sysctl', '-n', 'hw.model', 'hw.ncpu', 'hw.memsize'])]
        disassembly, decoded, hashes = {}, {}, {}
        for access, suffix in (('mdspan', ''), ('manual', '_manual')):
            binary = build/'bin'/('strategy_replay'+suffix)
            obj = build/'studies/strategy-loop/CMakeFiles'/('strategy_core'+suffix+'.dir')/'src/replay.cpp.o'
            for source, target in ((binary, out/access), (obj, out/(access+'.o'))):
                shutil.copy2(source, target)
                hashes[target.name] = digest(target)
            tool = command(['xcrun', 'llvm-objdump', '--disassemble', '--reloc', '--demangle', obj])
            if tool.get('returncode') != 0:
                raise RuntimeError('disassembly failed')
            manifest['executions'].append(tool)
            disassembly[access] = tool['stdout']
            (out/(access+'.disassembly.txt')).write_text(tool['stdout'])
            decoded[access] = replay_instructions(tool['stdout'])
        a, b = decoded['mdspan'], decoded['manual']
        comparison = dict(object_bytes_equal=hashes['mdspan.o'] == hashes['manual.o'],
                          instruction_counts={k: len(v) for k, v in decoded.items()},
                          mnemonic_counts={k: dict(Counter(i['assembly'].split()[0] for i in v)) for k, v in decoded.items()},
                          same_instruction_addresses=[i['address'] for i in a] == [i['address'] for i in b],
                          differences=[dict(mdspan=x, manual=y) for x, y in zip(a, b) if x != y])
        save(out/'code-comparison.json', comparison)
        (out/'disassembly.diff').write_text(''.join(difflib.unified_diff(
            disassembly['mdspan'].splitlines(True), disassembly['manual'].splitlines(True),
            fromfile='mdspan', tofile='manual')))
        manifest['artifact_sha256'] = hashes
        manifest['processes_before'] = command(['ps', '-A', '-o', 'pid=,pcpu=,comm=', '-r'])
        identity = None

        def worker(access, order, layout, repetition, timed):
            nonlocal identity
            label = f'{"pilot" if timed else "verify"}-r{repetition}-{order}-{layout}-{access}'
            argv = [str(out/access), '--bars', str(out/dataset['file']), '--spans', ','.join(map(str, range(2,97,2))),
                    '--count', '1128', '--layout', layout, '--order', order, '--capital', '1000',
                    '--fee', '.0001', '--output', str(out/label)] + (['--time'] if timed else [])
            record = dict(id=label, command=argv, started_utc=utc())
            manifest['executions'].append(record); checkpoint()
            run = subprocess.run(argv, capture_output=True, text=True, timeout=min(30, max(.01,900-(time.monotonic()-started))))
            (out/(label+'.stdout.json')).write_text(run.stdout)
            (out/(label+'.stderr.txt')).write_text(run.stderr)
            record.update(returncode=run.returncode, finished_utc=utc())
            run.check_returncode()
            value = json.loads(run.stdout)
            required = dict(timed=timed, order=order, layout=layout, bars=32768, windows=48,
                            configs=1128, eligible_bars=32672, capital=1000.0, fee=.0001)
            if any(value[k] != v for k, v in required.items()):
                raise ValueError('worker identity/contract mismatch')
            if (value['prepared_ns'] != value['replay_ns']+value['summary_ns'] or
                    value['whole_ns'] != sum(value[k+'_ns'] for k in ('feature','layout','setup','replay','summary')) or
                    (timed and value['replay_ns'] <= 0) or (not timed and value['whole_ns'] != 0) or
                    value['peak_rss_bytes'] > 536870912):
                raise ValueError('interval or RSS gate failed')
            summary = out/(label+'.summary.csv')
            error = audit_rows(read_rows(summary), expected)
            if identity is None:
                identity = digest(summary)
            if digest(summary) != identity:
                raise ValueError('C++ outputs differ across access/traversal/layout/repetition')
            manifest['observations'].append(dict(access=access, repeat=repetition, **value,
                                                summary_sha256=identity, maximum_reference_absolute_error=error))
            checkpoint()

        for order, layout in CANDIDATES:
            for access in ('mdspan', 'manual'):
                worker(access, order, layout, 0, False)
        print('Eight full-scale output gates passed.', flush=True)
        if args.pilot:
            if list((ROOT/'build').glob('*/.main-campaign.lock')) or (ROOT/'build/.strategy-campaign.lock').exists():
                raise RuntimeError('another campaign holds a lock')
            for lock in (ROOT/'build/.strategy-campaign.lock', ROOT/'build/barrier-release/.main-campaign.lock',
                         ROOT/'build/precision-release/.main-campaign.lock'):
                lock.parent.mkdir(parents=True, exist_ok=True)
                with lock.open('x') as stream:
                    locks.append(lock)
                    json.dump(dict(pid=os.getpid(), output=str(out)), stream)
            manifest['timer_calibration'] = [command([out/k, '--timer']) for k in ('mdspan','manual')]
            for calibration in manifest['timer_calibration']:
                if calibration.get('returncode') != 0:
                    raise RuntimeError('timer calibration failed')
                timer = json.loads(calibration['stdout'])
                if not timer['steady'] or timer['minimum_positive_ns'] <= 0:
                    raise RuntimeError('timer calibration lacks a usable steady clock')
            entry = environment(); mode = power_mode(entry)
            manifest['allow_battery'] = args.allow_battery
            manifest['power_condition'] = mode
            quiet_start = None; waiting = time.monotonic()
            print('Waiting for 60 seconds of sampled load <= half logical CPUs.', flush=True)
            while time.monotonic()-waiting <= 600:
                sample = environment(); sample['phase'] = 'quiet_entry'
                manifest['environment'].append(sample)
                if not power_ok(sample, args.allow_battery) or power_mode(sample) != mode:
                    raise RuntimeError('power condition changed or unsupported')
                now = time.monotonic()
                if sample['load_average'][0] <= (os.cpu_count() or 1)*.5:
                    if quiet_start is None: quiet_start = now
                    if now-quiet_start >= 60: break
                else: quiet_start = None
                checkpoint(); time.sleep(15)
            else:
                raise RuntimeError('quiet entry not reached within 600 seconds')
            manifest['quiet_wait_seconds'] = time.monotonic()-waiting
            # Balanced candidate order, paired AB/BA access order alternated by
            # repeat and candidate. Each pair is two independent fresh processes.
            plan = [dict(repeat=r, order=CANDIDATES[c][0], layout=CANDIDATES[c][1], access=access)
                    for r in range(4) for c in ORDERS[r]
                    for access in (('mdspan','manual') if (r+c)%2 == 0 else ('manual','mdspan'))]
            save(out/'pilot-plan.json', plan)
            manifest['pilot_plan_sha256'] = digest(out/'pilot-plan.json')
            for item in plan:
                sample = environment(); sample['phase'] = 'measurement'
                manifest['environment'].append(sample)
                if not power_ok(sample, args.allow_battery) or power_mode(sample) != mode:
                    raise RuntimeError('power condition changed')
                worker(item['access'], item['order'], item['layout'], item['repeat'], True)
        if source_files() != sources or any(digest(out/name) != h for name,h in hashes.items()):
            raise RuntimeError('frozen sources or copied build changed')
        for key in ('file', 'reference'):
            if digest(out/dataset[key]) != dataset[key+'_sha256']:
                raise RuntimeError('input/reference changed')
        manifest['status'] = 'complete'
        manifest['processes_after'] = command(['ps', '-A', '-o', 'pid=,pcpu=,comm=', '-r'])
        print('Completed; individual observations and disassembly retained.', flush=True)
    except Exception as error:
        manifest.update(status='failed', error=repr(error))
        raise
    finally:
        for lock in locks:
            lock.unlink()
        manifest.update(finished_utc=utc(), elapsed_seconds=time.monotonic()-started)
        save(out/'manifest.json', manifest)


if __name__ == '__main__':
    main()
