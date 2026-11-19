#!/usr/bin/env python3
"""Download QQQ 1-minute Alpaca bars for the strategy study. Python 3.10+, stdlib only.

Credentials: APCA_API_KEY_ID and APCA_API_SECRET_KEY.
Default: SIP, split-adjusted OHLCV, all bars returned by the feed (extended hours
included). Dates are New York calendar dates; --end is exclusive. No gap filling.
Completed monthly chunks are checksum-verified and reused on restart.
"""
import argparse
import csv
from datetime import date, datetime, time as day_time, timedelta, timezone
from decimal import Decimal
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

NY = ZoneInfo('America/New_York')
UTC = timezone.utc
API = 'https://data.alpaca.markets/v2/stocks/QQQ/bars'
FIELDS = ['timestamp', 'timestamp_utc', 'open', 'high', 'low', 'close',
          'volume', 'trade_count', 'vwap']
DOCS = 'https://docs.alpaca.markets/us/reference/stockbarsingle-1'


def stamp(value):
    return value.astimezone(UTC).isoformat().replace('+00:00', 'Z')


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as file:
        for block in iter(lambda: file.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def save_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def month_ranges(start, end):
    current = start
    while current < end:
        following = date(current.year + (current.month == 12), current.month % 12 + 1, 1)
        stop = min(following, end)
        yield (datetime.combine(current, day_time(), NY).astimezone(UTC),
               datetime.combine(stop, day_time(), NY).astimezone(UTC))
        current = stop


def get_json(params):
    """Bounded retries for temporary errors; never fall back to a different feed."""
    request = Request(API + '?' + urlencode(params), headers={
        'APCA-API-KEY-ID': os.environ['APCA_API_KEY_ID'],
        'APCA-API-SECRET-KEY': os.environ['APCA_API_SECRET_KEY'],
        'Accept': 'application/json', 'User-Agent': 'QQQ-history-export/1.0'})
    for attempt in range(6):
        try:
            with urlopen(request, timeout=45) as response:
                # Preserve decimal values rather than round-tripping prices through float.
                return json.loads(response.read(), parse_float=Decimal)
        except HTTPError as error:
            if error.code in (401, 403):
                raise RuntimeError(f'Alpaca HTTP {error.code}: check API keys and SIP data access.') from None
            if error.code != 429 and not 500 <= error.code < 600:
                raise RuntimeError(f'Alpaca HTTP {error.code}; request failed (see {DOCS}).') from None
            if attempt == 5:
                raise RuntimeError(f'Alpaca HTTP {error.code}; retry budget exhausted.') from None
            retry = error.headers.get('Retry-After', '')
            delay = min(60.0, max(1.0, float(retry))) if retry.isdigit() else min(60, 2 ** (attempt + 1))
        except (URLError, TimeoutError) as error:
            if attempt == 5:
                raise RuntimeError('Network request failed after six attempts.') from error
            delay = min(60, 2 ** (attempt + 1))
        print(f'Temporary request failure; retrying in {delay:g}s.', flush=True)
        time.sleep(delay)
    raise AssertionError('unreachable')


def number(value, field, integer=False):
    result = Decimal(str(value))
    if not result.is_finite() or result < 0 or (field in ('open', 'high', 'low', 'close') and result == 0):
        raise ValueError(f'Invalid {field} in Alpaca response')
    if integer and result != result.to_integral_value():
        raise ValueError(f'Non-integer {field}')
    return str(result)


def normalize(bar):
    instant = datetime.fromisoformat(bar['t'].replace('Z', '+00:00'))
    if instant.tzinfo is None:
        raise ValueError('Bar timestamp lacks timezone')
    instant = instant.astimezone(UTC)
    if instant.second or instant.microsecond:
        raise ValueError('Bar timestamp is not a minute boundary')
    row = dict(timestamp=str(int(instant.timestamp())), timestamp_utc=stamp(instant))
    for short, field in [('o', 'open'), ('h', 'high'), ('l', 'low'), ('c', 'close'), ('v', 'volume')]:
        row[field] = number(bar[short], field)
    row['trade_count'] = number(bar['n'], 'trade_count', integer=True) if bar.get('n') is not None else ''
    row['vwap'] = number(bar['vw'], 'vwap') if bar.get('vw') is not None else ''
    if not Decimal(row['low']) <= min(Decimal(row['open']), Decimal(row['close'])) <= max(Decimal(row['open']), Decimal(row['close'])) <= Decimal(row['high']):
        raise ValueError('Inconsistent OHLC values')
    return instant, row


def download_month(folder, start, end, feed, adjustment, fetch=None):
    fetch = fetch or get_json
    tag = start.astimezone(NY).strftime('%Y-%m')
    chunk = folder / f'{tag}.csv'
    record = folder / f'{tag}.json'
    raw = folder / f'{tag}.responses.jsonl.gz'
    query = dict(timeframe='1Min', start=stamp(start),
                 end=stamp(end - timedelta(microseconds=1)), limit=10000,
                 adjustment=adjustment, feed=feed, sort='asc')
    if record.exists():
        previous = json.loads(record.read_text())
        if (previous['query'] != query or previous['csv_sha256'] != sha256(chunk)
                or previous['responses_sha256'] != sha256(raw)):
            raise ValueError(f'{tag}: existing chunk/config hash mismatch; use a new output directory')
        print(f'{tag}: reuse {previous["rows"]:,} checked rows', flush=True)
        return previous
    partial = chunk.with_suffix('.csv.part')
    raw_partial = raw.with_suffix('.gz.part')
    seen_tokens, previous_row = set(), None
    rows = duplicates = pages = 0
    first_timestamp = last_timestamp = None
    page_query = dict(query)
    with partial.open('w', newline='') as file, gzip.open(raw_partial, 'wt', encoding='utf-8') as source:
        writer = csv.DictWriter(file, FIELDS, lineterminator='\n')
        writer.writeheader()
        while True:
            payload = fetch(page_query)
            # Decimal values are strings in this retained decoded-response representation.
            source.write(json.dumps(dict(query=page_query, response=payload), default=str) + '\n')
            if payload.get('symbol') != 'QQQ' or not isinstance(payload.get('bars'), (list, type(None))):
                raise ValueError(f'{tag}: unexpected response schema/symbol')
            pages += 1
            for bar in payload.get('bars') or []:
                instant, row = normalize(bar)
                if not start <= instant < end:
                    raise ValueError(f'{tag}: bar outside the requested monthly interval')
                if previous_row and int(row['timestamp']) <= int(previous_row['timestamp']):
                    if row == previous_row:
                        duplicates += 1
                        continue
                    raise ValueError(f'{tag}: out-of-order or conflicting duplicate bar')
                writer.writerow(row)
                rows += 1
                first_timestamp = first_timestamp or row['timestamp_utc']
                last_timestamp = row['timestamp_utc']
                previous_row = row
            token = payload.get('next_page_token')
            if not token:
                break
            if not isinstance(token, str) or token in seen_tokens:
                raise ValueError(f'{tag}: repeated/invalid pagination token')
            seen_tokens.add(token)
            page_query = dict(query, page_token=token)
    if rows == 0:
        raise ValueError(f'{tag}: no bars returned; inspect credentials, feed and coverage')
    partial.replace(chunk)
    raw_partial.replace(raw)
    metadata = dict(query=query, csv_file=chunk.name, responses_file=raw.name,
                    rows=rows, pages=pages, identical_duplicates_skipped=duplicates,
                    first_timestamp=first_timestamp, last_timestamp=last_timestamp,
                    fetched_at=stamp(datetime.now(UTC)), csv_sha256=sha256(chunk),
                    responses_sha256=sha256(raw))
    save_json(record, metadata)
    print(f'{tag}: downloaded {rows:,} rows in {pages} pages', flush=True)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--start', type=date.fromisoformat, default=date(2023, 1, 1), help='inclusive New York date')
    parser.add_argument('--end', type=date.fromisoformat, default=date(2026, 1, 1), help='exclusive New York date')
    parser.add_argument('--feed', choices=['sip', 'iex'], default='sip')
    parser.add_argument('--adjustment', choices=['raw', 'split', 'dividend', 'all'], default='split')
    parser.add_argument('--output', type=Path, help='default: local/data/alpaca/QQQ_1Min_<dates>_<feed>_<adjustment>')
    args = parser.parse_args()
    if args.start >= args.end:
        parser.error('--start must precede --end')
    for name in ('APCA_API_KEY_ID', 'APCA_API_SECRET_KEY'):
        if not os.environ.get(name):
            parser.error(f'Set {name} in the environment first')
    output = args.output or Path('local/data/alpaca') / f'QQQ_1Min_{args.start}_{args.end}_{args.feed}_{args.adjustment}'
    output.mkdir(parents=True, exist_ok=True)
    spec = dict(symbol='QQQ', timeframe='1Min', feed=args.feed, adjustment=args.adjustment,
                start_inclusive=str(args.start), end_exclusive=str(args.end),
                date_timezone='America/New_York', timestamp_timezone='UTC',
                sessions='all bars provided by chosen feed; no regular-session filter',
                missing_minutes='not filled', endpoint=API)
    lock = output / '.download.lock'
    # Exclusive creation prevents two invocations from overwriting a partial chunk.
    try:
        lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        parser.error(f'{lock} exists. Check that no downloader is running before removing a stale lock.')
    with os.fdopen(lock_fd, 'w') as stream:
        stream.write(str(os.getpid()) + '\n')
    manifest = output / 'manifest.json'
    try:
        if manifest.exists() and json.loads(manifest.read_text())['request'] != spec:
            raise ValueError('Output directory belongs to a different request; choose another --output')
        state = dict(status='in_progress', request=spec, command=[sys.executable, *sys.argv],
                     python=sys.version, downloader_sha256=sha256(__file__),
                     months=[], started_at=stamp(datetime.now(UTC)), documentation=DOCS)
        save_json(manifest, state)
        chunks = output / 'months'
        chunks.mkdir(exist_ok=True)
        for start, end in month_ranges(args.start, args.end):
            state['months'].append(download_month(chunks, start, end, args.feed, args.adjustment))
            save_json(manifest, state)
        full = output / 'QQQ_1Min.csv'
        replay = output / 'QQQ_1Min_open_close.csv'
        full_partial, replay_partial = full.with_suffix('.csv.part'), replay.with_suffix('.csv.part')
        count, prior = 0, None
        with full_partial.open('w', newline='') as all_file, replay_partial.open('w', newline='') as replay_file:
            all_writer = csv.DictWriter(all_file, FIELDS, lineterminator='\n')
            simple_writer = csv.DictWriter(replay_file, ['timestamp', 'open', 'close'], lineterminator='\n')
            all_writer.writeheader(); simple_writer.writeheader()
            for month in state['months']:
                with (chunks / month['csv_file']).open(newline='') as stream:
                    for row in csv.DictReader(stream):
                        current = int(row['timestamp'])
                        if prior is not None and current <= prior:
                            raise ValueError('Merged timestamps are not strictly increasing')
                        all_writer.writerow(row)
                        simple_writer.writerow({k:row[k] for k in ('timestamp', 'open', 'close')})
                        prior = current; count += 1
        full_partial.replace(full); replay_partial.replace(replay)
        assert count == sum(m['rows'] for m in state['months'])
        state.update(status='complete', rows=count, finished_at=stamp(datetime.now(UTC)),
                     outputs={p.name:sha256(p) for p in (full, replay)},
                     caveat='API pagination completed; exchange-calendar gap auditing and regular-session filtering are separate steps.')
        save_json(manifest, state)
        print(f'Complete: {count:,} bars\n{full.resolve()}\n{replay.resolve()}', flush=True)
    finally:
        lock.unlink()


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, OSError, KeyError) as error:
        print(f'Error: {error}', file=sys.stderr)
        sys.exit(1)
