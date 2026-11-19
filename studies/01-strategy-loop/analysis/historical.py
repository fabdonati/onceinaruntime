"""Audit the supplied Alpaca QQQ export and freeze regular-session workloads."""
import argparse
import csv
from datetime import date, datetime, time, timedelta, timezone
import hashlib
from itertools import zip_longest
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

from inputs import write_bars

STUDY = Path(__file__).resolve().parents[1]
CALENDAR = STUDY / 'configs/nasdaq-sessions-2023-2025.json'
PROFILES = ('jump', 'directional', 'low-directionality')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def schedule(calendar):
    day, end = date.fromisoformat(calendar['start']), date.fromisoformat(calendar['end_exclusive'])
    holidays, early = set(calendar['holidays']), set(calendar['early_closes'])
    tz = ZoneInfo(calendar['timezone'])
    result = {}
    while day < end:
        if day.weekday() < 5 and str(day) not in holidays:
            opening = datetime.combine(day, time.fromisoformat(calendar['regular_open']), tz)
            closing = datetime.combine(day, time.fromisoformat(calendar['early_close'] if str(day) in early else calendar['regular_close']), tz)
            result[str(day)] = (int(opening.timestamp()), int(closing.timestamp()))
        day += timedelta(days=1)
    return result


def validate_row(row):
    t = int(row['timestamp'])
    values = {k: float(row[k]) for k in ('open', 'high', 'low', 'close', 'vwap')}
    if t % 60 or any(not math.isfinite(v) or v <= 0 for v in values.values()):
        raise ValueError('unaligned timestamp or invalid price')
    if not (values['low'] <= min(values['open'], values['close']) <=
            max(values['open'], values['close']) <= values['high']):
        raise ValueError('inconsistent OHLC bounds')
    if int(row['trade_count']) <= 0 or not math.isfinite(float(row['volume'])) or float(row['volume']) <= 0:
        raise ValueError('invalid trade count or volume')
    if datetime.fromisoformat(row['timestamp_utc'].replace('Z', '+00:00')).timestamp() != t:
        raise ValueError('timestamp columns disagree')
    return t, values['open'], values['close']


def select_windows(bars, size=32768, short=4096):
    if short > size or short < 2:
        raise ValueError('invalid window lengths')
    blocks = []
    for offset in range(0, len(bars)-size+1, size):
        chunk = bars[offset:offset+size]
        diffs = [math.log(b[2]/a[2]) for a, b in zip(chunk, chunk[1:])]
        total = math.fsum(abs(v) for v in diffs)
        jump = max(range(len(diffs)), key=lambda i: abs(diffs[i])) + 1
        blocks.append(dict(block=len(blocks), offset=offset, bars=size,
            start=chunk[0][0], end=chunk[-1][0],
            directionality=abs(math.log(chunk[-1][2]/chunk[0][2]))/total if total else 0.,
            abruptness=abs(diffs[jump-1]), jump_index=jump,
            jump_previous_bar=chunk[jump-1], jump_bar=chunk[jump]))
    if len(blocks) < 3:
        raise ValueError('fewer than three complete historical blocks')
    jump = min(blocks, key=lambda b: (-b['abruptness'], b['start']))
    directional = min((b for b in blocks if b != jump), key=lambda b: (-b['directionality'], b['start']))
    low = min((b for b in blocks if b not in (jump, directional)), key=lambda b: (b['directionality'], b['start']))
    datasets = []
    for profile, block in zip(PROFILES, (jump, directional, low)):
        crop = (max(0, min(size-short, block['jump_index']-short//2))
                if profile == 'jump' else (size-short)//2)
        for n, relative in ((short, crop), (size, 0)):
            offset = block['offset'] + relative
            datasets.append(dict(dataset_id=f'qqq-{profile}-n{n}', profile=profile, bars=n,
                parent_block=block['block'], offset=offset, parent_offset=relative,
                start=bars[offset][0], end=bars[offset+n-1][0]))
    return blocks, datasets


def prepare(source, output):
    output.mkdir(parents=True, exist_ok=False)
    provider = json.loads((source/'manifest.json').read_text())
    request = provider['request']
    required = dict(symbol='QQQ', timeframe='1Min', feed='sip', adjustment='split',
                    start_inclusive='2023-01-01', end_exclusive='2026-01-01')
    if provider['status'] != 'complete' or any(request.get(k) != v for k, v in required.items()):
        raise ValueError('unexpected provider request or incomplete export')
    for name, expected in provider['outputs'].items():
        if digest(source/name) != expected:
            raise ValueError('merged input hash mismatch: '+name)
    for month in provider['months']:
        for name, key in (('csv_file', 'csv_sha256'), ('responses_file', 'responses_sha256')):
            if digest(source/'months'/month[name]) != month[key]:
                raise ValueError('monthly source hash mismatch')
    calendar = json.loads(CALENDAR.read_text())
    sessions = schedule(calendar)
    expected = {t for start, end in sessions.values() for t in range(start, end, 60)}
    bars, seen, count, outside, previous = [], set(), 0, 0, None
    with (source/'QQQ_1Min.csv').open() as full, (source/'QQQ_1Min_open_close.csv').open() as simple:
        for row, projection in zip_longest(csv.DictReader(full), csv.DictReader(simple)):
            if row is None or projection is None:
                raise ValueError('projection length mismatch')
            t, opening, closing = validate_row(row)
            if any(row[k] != projection[k] for k in ('timestamp', 'open', 'close')):
                raise ValueError('projection differs from full source')
            if previous is not None and t <= previous:
                raise ValueError('duplicate or out-of-order source timestamp')
            previous = t
            count += 1
            if t in expected:
                bars.append((t, opening, closing)); seen.add(t)
            else:
                outside += 1
    missing = sorted(expected-seen)
    audit = dict(source_rows=count, regular_rows=len(bars), outside_regular_rows=outside,
                 sessions=len(sessions), expected_regular_minutes=len(expected),
                 missing_minutes=missing, gap_fill=False, projection_exact=True,
                 monthly_hashes_checked=len(provider['months']))
    (output/'audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    if count != provider['rows'] or missing:
        raise ValueError('row count mismatch or unresolved regular-session missing minutes; see audit.json')
    write_bars(output/'regular.csv', bars)
    blocks, datasets = select_windows(bars)
    for item in datasets:
        file = output/(item['dataset_id']+'.csv')
        write_bars(file, bars[item['offset']:item['offset']+item['bars']])
        item.update(file=file.name, file_sha256=digest(file))
    manifest = dict(schema_version=1, status='complete', input_kind='historical',
        instrument='QQQ', provider='Alpaca', feed='sip', adjustment='split',
        timestamp_convention='UTC epoch seconds at bar start', session='regular Nasdaq equities',
        accounting='price only; no dividends or live execution claim',
        source_manifest_sha256=digest(source/'manifest.json'), source_outputs=provider['outputs'],
        calendar_sha256=digest(CALENDAR), normalizer_sha256=digest(__file__),
        audit=audit, regular_sha256=digest(output/'regular.csv'),
        candidate_blocks=blocks, incomplete_tail_rows=len(bars)%32768, datasets=datasets,
        selection='Highest abruptness, then highest remaining directionality, then lowest remaining directionality; earliest timestamp wins ties.',
        references=['https://docs.alpaca.markets/us/reference/stockbarsingle-1',
                    'https://alpaca.markets/learn/stock-minute-bars', *calendar['sources']])
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    m = prepare(args.source, args.output)
    print(json.dumps(dict(audit=m['audit'], datasets=m['datasets']), indent=2))


if __name__ == '__main__':
    main()
