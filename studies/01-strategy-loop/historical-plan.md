# Historical workload extension

Status: completed, 17 November 2026. The supplied QQQ/Alpaca export resolves the
source choice below. The implemented matrix passed 48 untimed checks, 48 pilot
and 384 main observations. Source, selection and timing protocols were frozen
before timing; see [findings](findings.md) for outcomes. Earlier synthetic
campaigns remain separate.

## Question and scope

Does the observed traversal/layout ordering persist when the same independent
EMA accounts consume different historical price paths? Does its magnitude vary
with measured position-change frequency and holding behaviour?

Retain the four C++23 implementations, 48 shared EMA spans (2..96 by 2), double
precision, common 96-bar warm-up, next-open execution, fees and required outputs.
Keep one strategy family. Different histories and parameter settings broaden
the workload without adding a second trading algorithm. No manual SIMD, threads,
shared capital, live execution or strategy-profitability study is included.

Repeated ordering would extend the evidence to the selected historical inputs.
A reversal, overlapping timing distributions or inconsistent ordering is equally
reportable. Three histories cannot establish behaviour across markets generally.
Activity metrics can describe a possible explanation, not prove a cache or
branch-prediction mechanism.

## 1. Resolve data access and freeze the input contract

Selected source: **QQQ, Alpaca SIP one-minute trade bars, split-adjusted,
2023-01-01 inclusive through 2026-01-01 exclusive**. The author supplied the export,
replacing the initially proposed SPY acquisition target. No new subscription or
provider integration was needed. The downloader record retains its command,
retrieval time, 36 monthly response/CSV hashes and merged output hashes.

The [Alpaca bar API](https://docs.alpaca.markets/us/reference/stockbarsingle-1)
defines the adjustment request; [Alpaca's minute-bar explanation](https://alpaca.markets/learn/stock-minute-bars)
describes timestamps at the start of the minute. All-hours exports remain under
ignored `local/data/alpaca/`; `analysis/historical.py` writes a new canonical
snapshot under `local/data/strategy-loop/qqq-rth-20261117/`.

The bounded Nasdaq calendar in `configs/nasdaq-sessions-2023-2025.json` handles
DST, eight early closes and the exceptional 9 January 2025 closure. Inclusion is
bar start >= session open and < session close: the 16:00 bar is excluded, so the
last included minute's close is not claimed to be the official auction close.
The result contains 291,840 expected minutes across 752 sessions, none missing;
348,364 source rows are outside those intervals. No filling or synthetic rows.

The input manifest must record:

- Provider, instrument/contract ID, currency, interval, price field definition,
  session filter, timestamp timezone and whether timestamps denote bar start/end.
- Requested and actual date coverage, retrieval command/time, source hashes,
  normalizer revision, canonical CSV hash and row count.
- Split/dividend convention applied consistently to both open and close. Prefer
  split-adjusted trade prices without dividend adjustment if the source supports
  that convention; otherwise document and resolve the convention first. Never
  combine raw opens with adjusted closes. The current account model omits
  dividends, so account outcomes remain a price-only execution model.
- Session calendar/source, missing-bar audit, duplicate/conflict audit, and any
  rejected or incomplete windows. Raw inputs stay out of Git; public exports
  contain only material appropriate for distribution.

Normalize to the existing `timestamp,open,close` CSV schema: UTC integer seconds,
finite positive prices, strictly increasing unique times. Preserve chronology
and actual overnight/weekend gaps. Use the provider's session schedule and
Python `zoneinfo` to handle DST/early closes; do not assume every day has the
same number of bars. Completed bars only. Merge identical download-boundary
duplicates with an audit count; reject conflicting duplicates. Investigate
unexpected gaps or suspicious prints rather than silently filling them.

For this study an EMA span counts available bars, not elapsed clock minutes.
The next bar's open may be the next session's open. Accounts carry across sessions;
the existing model does not add an overnight reset or extra trades.

If access or data quality is unresolved after a short acquisition feasibility
check, record the gap and settle the source before dependent work. Do not quietly
substitute daily bars, synthetic rows, another market or repeated short histories.

## 2. Select three windows without using runtime or strategy returns

Freeze the candidate pool after normalization. Divide it chronologically into
non-overlapping blocks of 32,768 accepted bars; record the incomplete tail and
reject blocks with unresolved data-quality issues. Require at least three valid
blocks. These blocks are repeatable benchmark windows, not claims that markets
remain in one regime for their full duration.

Compute from closing prices only:

- Directionality: `abs(log(last/first)) / sum(abs(diff(log(close))))`.
  Define a zero-denominator block as zero directionality.
- Abruptness: largest absolute consecutive close-to-close log return, including
  genuine session gaps. Check the candidate jump against the source and corporate
  action record before treating it as a market observation.

Select in this fixed order: the most abrupt valid block; the most directional
remaining block; the least directional remaining block. Break ties by earliest
start timestamp. Record scores and the entire candidate ranking. Call these
the jump, directional and low-directionality profiles. Do not promise frequent
EMA crossings in the last profile until activity metrics establish that.

For each selected long block, extract a nested 4,096-bar window. Use its central
4,096 bars for directional/low-directionality profiles. For the jump profile,
center on the designated jump, clamped within the parent block. Record the exact
offset, timestamp bounds and hashes. No performance or P&L determines a crop.
If the jump falls in the short window's warm-up, report that boundary limitation;
do not pretend it is an executed trading event or move it after seeing results.

Initialize each N independently using the same documented EMA seed and 96-bar
warm-up. Thus the short and long runs are nested datasets, not independent market
samples or a pure memory-size intervention. Profile metrics must be reported for
each N/K combination; a shorter crop need not share its parent's behaviour.

## 3. Changes to the experiment

| Location | Planned change | Completion check |
| --- | --- | --- |
| `analysis/inputs.py` plus one `analysis/historical.py` module | Normalize one selected source, audit sessions, select windows and emit manifests | Deterministic bytes/hashes; malformed and ambiguous inputs rejected |
| `configs/historical-pilot.json`, `configs/historical-main.json` | Separate frozen historical plans with dataset IDs and manifest hashes | Exact matrix validated; missing identities/hashes cannot start a run |
| `analysis/run.py` | Add a bounded historical mode; consume local files and identify workers by dataset ID, not fabricated seeds | Original synthetic IDs/plans still reproduce; all historical files hash-checked |
| `analysis/profiles.py` | Compute activity metrics from EMA targets outside timed code | Small hand-worked cases agree with account traces |
| `analysis/plot_historical.py` | Audit datasets by manifest identity and render historical comparisons with power/data labels | Reject missing, altered, mixed-condition or incomplete records |
| `tests/test_historical.py`, `tests/test_profiles.py`, `tests/test_runner.py` | Cover conversion, profile accounting, campaign identities and old-plan compatibility | Debug checks and independent historical reference gate pass |
| Study docs/results/figures | Add provenance, bounded findings, figure captions and reproduction commands | Every numerical article claim maps to retained observations |

The existing C++ CLI already reads timestamped open/close CSVs. No C++ hot-loop
change is expected. Keep canonical feature preparation and physical layout
materialization identical across all candidates. Historical mode should make
only the explicit extension above; do not turn the runner into a generic
benchmark framework or loosen the old frozen configurations.

Store a schema version, `input_kind=historical`, dataset/profile IDs, input
manifest hash and power condition on new records. Resolve reference filenames
through the dataset manifest. Keep the old seed-based records readable with their
original validation rules; `seed` is not an identity for market data.

## 4. Compute workload descriptors outside timing

For each profile, N and K, use the same canonical features and eligible bars as
the engine. Record per-configuration metrics and clearly defined aggregates:

| Metric | Definition |
| --- | --- |
| Opening position changes per 1,000 updates | Entries/exits at opens divided by `K*(N-96)`, times 1,000; include initial entry from cash, exclude forced final-close liquidation |
| Fraction holding the asset | Count eligible strategy-bars with a long position after opening execution, divided by `K*(N-96)` |
| Holding length | Median and quartiles of completed consecutive long spells, in eligible bars; record final open/censored spells separately |
| Clustering of transitions | Opening transitions aggregated across configurations in consecutive 256-bar blocks, normalized by actual block length and K |

Use bounded passes over boolean targets; retain summary tables and compact
transition series. Do not enable the current full diagnostic account trace for
all long histories: it repeatedly recomputes growing summaries and is suitable
for small correctness fixtures, not large profile extraction. Financial returns,
fees and drawdown remain output-parity checks, not window-selection criteria.

## 5. Verification and measurement matrix

First run normalizer fixtures for timestamp boundaries, DST, session gaps, early
closes, partial bars, non-positive/non-finite values and duplicate conflicts.
Use hand-worked target sequences to check no trades, always-long, alternating
positions, initial entry, final liquidation and censored holding periods.

Compare small real-data excerpts through all four C++ trace routes and the
independent ledger, including one overnight boundary. Each excerpt starts its
own documented initialization; do not compare a reset excerpt to an interior
slice of a differently initialized full run. Then compare every ordered summary
in all **48 untimed historical workers** (3 profiles × 2 N × 2 K × 4 variants).
Use existing exact discrete checks and floating tolerances, with no relaxation
after observing failures.

Run `cmake --preset debug`, `cmake --build --preset debug`, `ctest --preset debug`.
If C++ correctness code changes prove necessary, run the sanitizer preset too.
Confirm the release executable, compiler flags and source/build hashes before
timing. Existing timing boundaries and required outputs remain unchanged.

| Dimension | Frozen proposal |
| --- | --- |
| Historical profiles | 3 selected windows from one instrument |
| N, including warm-up | 4,096 and 32,768 bars |
| K | 64 and 1,128; existing lexicographic prefixes |
| W | 48 shared EMA windows, fixed at every K |
| Variants | Strategy/event traversal × history/snapshot storage |
| Main repetitions | 8 fresh processes per case |
| Main total | **384 observations** |

Before main timing, run one separately labelled **48-observation pilot**:
3 profiles × largest N × largest K × 4 candidates × 4 balanced repetitions.
It checks new data-path operation, duration and environmental conditions. Retain
it separately from the main run. Freeze final manifests and execution order
before timing; no extra repetition counts or replacement windows based on a
preferred outcome. There are 48 untimed checks plus 48 pilot and 384 main timing
observations; acquisition and profile calculations are not benchmark samples.

Reuse the four-row balanced candidate order twice for the main run. Rotate the
12 profile/N/K blocks across repetitions, recording the complete order, so one
profile does not always occur late. All runs are sequential. Keep the common
warm-up and fresh-process preparation policy; preserve raw observations.

Retain existing caps: 900 seconds per campaign, 30 seconds per worker, 512 MiB
worker RSS, 256 MiB campaign evidence and 1 GiB disk reserve. Wait at most ten
minutes for a full minute of load samples <=4. Record power, load, thermal-query
results and five-second process samples. Use temporary local evidence output
and archive with hash verification afterwards. No system settings or unrelated
processes are changed.

Battery operation is already authorized. Choose and record the actual power
source before each campaign; hold that mode throughout. Preserve a power-change
or other failed campaign without selectively dropping samples. Low recorded
load is not full CPU isolation. If sustained interference returns, retain it and
report the limitation rather than automatically rerun. Do not pool historic,
synthetic, AC and battery distributions as identical conditions.

## 6. Article and figure changes after evidence exists

Keep the article's question about computing the same accounts efficiently.
Add a short explanation of why input paths change the amount/pattern of account
work, followed by actual profile descriptors. Supporting historical finance
examples remain simplified bar-based execution, not an HFT latency model.

- Show a compact three-profile price strip with date/instrument labels and
  measured position-change rates. Normalize prices only for this illustration;
  feed original canonical prices to the engine.
- Add a compact historical timing panel: within each layout plot
  `T_strategy / T_event` for each profile at matched N/K. Show raw matched repeat
  ratios and their descriptive median, with a parity line at 1. Keep absolute
  timings and complete computation cost available in the result table. Label
  normalization explicitly; do not substitute a ratio of medians for the median
  of paired ratios.
- Keep one full-cost view only if it affects interpretation, using actual stages
  from a complete representative run. Choose the directional profile, largest N,
  smallest K in advance, not whichever produces the largest visual difference.
- Retain the contour illustration as output context. If showing historical
  parameter contours, use the preselected directional profile/long history,
  disclose its price-only accounting, and use actual signed returns with one
  common scale across any compared panels. Never choose the most profitable
  window to decorate the article. Do not hard-code the synthetic -60..140% scale
  or relabel synthetic results as historical.

First reconcile the existing draft's synthetic results with the completed
battery reproduction. Add historical conclusions only after the new gate and
campaign complete. Report reversals, no change or inconclusive evidence directly;
elapsed time and trading activity alone do not establish hardware causality.

## Delivery order and effort

1. Confirm source access/semantics; freeze candidate pool and selection procedure.
2. Implement normalization, manifests and activity descriptors with small checks.
3. Extend historical runner/plot identities; verify old-plan compatibility and
   all historical outputs.
4. Execute one bounded pilot, then the frozen main campaign if its setup is valid.
5. Audit retained results; update figures, article, findings and status together.

The initial planning estimate was **10–15 hands-on hours**, assuming usable data
access; it is not a record of author time spent. The supplied export resolved
acquisition. Normalization, profiles, correctness, pilot/main measurement and
article/figure reconciliation are complete. The next step is author review of
the current draft and figures; additional strategy families are a separate study.
