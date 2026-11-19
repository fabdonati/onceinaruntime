# QQQ one-minute Alpaca export

Data acquisition tool for the [strategy study](../../README.md), prepared
17 November 2026. No third-party Python packages are required (Python 3.10+ with
timezone data). Downloaded data and credentials stay outside version control.

From the repository root, set `APCA_API_KEY_ID` and
`APCA_API_SECRET_KEY` in your shell, then run:

```sh
python3 studies/01-strategy-loop/tools/alpaca/download_qqq.py
```

Default request:

- QQQ, `1Min`, 1 January 2023 through 31 December 2025 inclusive, interpreted as
  America/New_York calendar dates. `--end 2026-01-01` is exclusive.
- Consolidated `sip` feed, with `split` adjustment on OHLCV. Dividends are not
  adjusted. Use `--adjustment raw` for unadjusted prices or `all` to request all
  Alpaca adjustments. Feed and adjustment are recorded; there is no silent
  fallback to IEX when SIP access fails.
- All bars returned by that feed, including available extended-hours bars.
  **This is not yet a regular-trading-hours dataset.** Preserve the full export;
  exchange-calendar filtering (including early closes) can be done afterwards.
- UTC timestamps, monthly requests with complete pagination, bounded retries,
  resumable completed months and checksum verification. Identical duplicates at
  page boundaries are counted and skipped; conflicting or unordered rows fail.
- No invented or forward-filled minutes. A completed request does not certify
  every expected exchange minute; session/calendar coverage still needs auditing.

Default output directory:

`local/data/alpaca/QQQ_1Min_2023-01-01_2026-01-01_sip_split/`

| Output | Contents |
| --- | --- |
| `QQQ_1Min.csv` | UTC epoch seconds, ISO UTC time, OHLCV, trade count and VWAP |
| `QQQ_1Min_open_close.csv` | `timestamp,open,close` projection for subsequent study ingestion |
| `months/*.csv` and `months/*.json` | Monthly data, request details, pagination count, hashes and retrieval timestamps |
| `months/*.responses.jsonl.gz` | Decoded response pages and queries; decimals represented as strings |
| `manifest.json` | Request, progress/completion, command, source hash and merged output hashes |

Example short request to check access before the full download:

```sh
python3 studies/01-strategy-loop/tools/alpaca/download_qqq.py \
  --start 2023-01-03 --end 2023-01-04 \
  --output local/data/alpaca/qqq-access-check
```

Run the original command again to resume after an ordinary interruption.
Incomplete months are fetched again; completed months are reused after checking
their hashes. A request must retain its feed, adjustments and date interval in
the same output directory. Use a new output directory for a fresh data snapshot
or different settings. API responses can be revised by the provider over time;
resumed exports retain each month's retrieval timestamp rather than claiming one
atomic provider snapshot.

The lock prevents two simultaneous writers. After a force-kill, only remove a
stale `.download.lock` once the corresponding downloader is no longer running.
Credentials are read from the environment, not stored in files or manifests.

Offline validation:

```sh
python3 -m unittest discover -s studies/01-strategy-loop/tests -p 'test_download_qqq.py' -v
```

These tests also run with the study's standard `ctest --preset debug` checks.

References: [Alpaca historical bars](https://docs.alpaca.markets/us/reference/stockbarsingle-1)
and [bar aggregation / feed FAQ](https://docs.alpaca.markets/us/docs/market-data-faq).
The downloader has been prepared and tested with mocked responses; no authenticated
download has been performed as part of its preparation.
