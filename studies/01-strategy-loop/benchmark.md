# Reproducing the strategy study

Start with the five-bar example below. It uses both the C++23 replay engine
and a small input you can read by hand. The correctness suite compares the
engine with a Python ledger. Generated prices are enough to run the synthetic
benchmark. The historical comparison uses Alpaca QQQ bars.

Run commands from the repository root. Use the [setup in the root README](../../README.md)
for GCC, CMake and Python. Timing requires stable AC by default. Use
`--allow-battery` for a separate battery run and keep its results separate
from AC results. See [findings](findings.md) for the earlier battery run.

## Correctness and a small worked run

```sh
cmake --preset debug
cmake --build --preset debug
ctest --preset debug
cmake --preset sanitize
cmake --build --preset sanitize
ctest --preset sanitize
```

CTest includes rational hand-calculated fee/EMA cases and a separate Python
transaction ledger. Small fixtures compare every feature and every diagnostic
field, including next-open decisions, quantities, fees, equity, running peaks
and trade counts. The four C++ variants must produce byte-identical CSV outputs.
Python comparisons require exact discrete fields and floating-point agreement
within `rel_tol=2e-12, abs_tol=1e-9`; EMA values are compared exactly. This small
tolerance accommodates the Python ledger's separate fee subtraction and summed
transactions. The no-trace code path is checked separately too.

CSV input has exactly `timestamp,open,close`: integer increasing timestamps and
finite positive prices. Diagnostic output is deliberately simple, without a
generic CSV library. Quoted fields, missing bars and adjustment conventions are
not inferred. A real-market file needs its provenance and price convention
documented separately. Example commands use the checked synthetic account:

```sh
mkdir -p build/strategy-account
build/debug/bin/strategy_replay \
  --bars studies/01-strategy-loop/examples/account.csv --spans 2,3 \
  --layout history --order strategy --trace \
  --output build/strategy-account/account
```

This writes `.features.csv`, `.trace.csv`, `.summary.csv` and prints JSON metadata.
Use `--layout snapshot` and/or `--order event` to select the other routes.
`--fee 0` reproduces the article's fee-free illustration. See the
[worked account](examples/account.md) for the actual one-basis-point arithmetic.

## Synthetic pilot settings

The [pilot configuration](configs/pilot.json) fixes the following settings.

- N = 4,096 and 32,768 synthetic bars; two independent generator seeds, 11 and 29.
- W = 48 spans, 2, 4, ..., 96. Common warm-up is 96 bars.
- K = 64, 256 and 1,128, nested lexicographic prefixes of fast<slow pairs.
  Every selected count references all 48 windows, although the distribution of
  pairs changes with K. The complete common feature population is always prepared.
- Four candidates; four fresh processes per candidate/input/count. A four-row
  Williams order balances each candidate's position and immediate predecessor.
  That is 192 observations, not 192 independent market histories.
- No extra warm-up replay. The feature preparation in each process naturally
  precedes its replay. No repeated short history, explicit SIMD or threading.
- 15-minute campaign cap, 30-second worker timeout, 256 MiB evidence cap and
  512 MiB observed worker peak-RSS stopping limit; 1 GiB free disk reserve.
- On this Mac: stable AC power and entry one-minute load <= half logical CPU
  count. Power is sampled between groups. Later load is recorded, not used to
  delete slow observations. No settings, affinity or unrelated processes change.
- Stop on any failed worker, invalid accounting, changed source/input/build,
  power failure or exceeded cap. Keep all prior observations and the failure.
  No automatic sample replacement, retry or main-campaign escalation.

The generator uses seeded integer random draws for opening gaps and intrabar
changes plus alternating drift. These are artificial bar indices and prices;
there is no inferred daily/minute interval or actual market-return claim. The
saved CSV bytes and hashes, rather than a promise of cross-platform `exp`
identity, define each input.

## Timing boundaries and memory

Read/validate CSV and select configurations before starting the clock. Within
one complete interval, measure canonical EMA preparation, physical layout
materialization, initial account allocation, replay, and ordered summary
construction. `prepared_ns = replay_ns + summary_ns` is the primary work interval;
divide it by `K * (N - 96)` for ns/strategy-bar. Required statistics are updated
inside replay. CSV serialization, file I/O and final buffer destruction are
outside both intervals. This is a computation cost, not end-to-end file latency.

History storage takes ownership of the canonical buffer. Snapshot storage
transposes that buffer into another allocation and releases canonical scratch
before replay. The complete interval includes this conversion and release.
Report N*W*8 feature bytes, one extra matrix of conversion scratch for snapshot,
actual bar/config/state/summary sizes, and observed process peak RSS. A live
buffer total differs from allocator overhead or process RSS. The simple common
canonical preparation is fixed here; alternative direct preparation is outside
this four-variant comparison.

The strategy-first route keeps an account local while traversing its history;
event-first updates the same state structure in the account array. The feature
mapping is statically selected outside the loop. One accounting definition
serves all routes. Diagnostics use a separate template instantiation and never
allocate a trace in a measured worker.

## Check the full workload and run the synthetic pilot

Build release once and run its correctness checks. The untimed matrix gate
computes independent ledger summaries for all 1,128 configurations on all four
input histories, then checks all four C++ routes at all three K. This complements
the small full-trace gate; it does not claim full scale traces were compared.

```sh
cmake --preset release
cmake --build --preset release
ctest --preset release
.venv/bin/python studies/01-strategy-loop/analysis/run.py --verify \
  --output build/strategy-verify
.venv/bin/python studies/01-strategy-loop/analysis/run.py --check
.venv/bin/python studies/01-strategy-loop/analysis/run.py --pilot \
  --verified build/strategy-verify --output build/strategy-pilot
```

Use new output directories. Verification and timing must match exact source,
binary, plan and input hashes. A source change requires another verification;
do not edit manifests to bypass the check. The runner saves every command,
individual observation, raw output, input/reference CSV, executable, compile
commands, CMake cache, public source snapshot and Git revision/dirty state.
Artifacts may contain local paths; retain original provenance privately.

Use the pilot to see how long a run takes and how much its timings vary.
Record any workload or repetition changes before starting a main campaign.

## Synthetic main campaign

The [main plan](measurement-plan.md) keeps N/K/W and the model fixed, adds seed 47,
and uses eight repetitions in two balanced cycles: 576 observations. It requires
all load samples over a full minute (at 15-second intervals) to pass the same
entry limit, waiting at most ten minutes within the fifteen-minute total cap.
If the quiet interval never arrives, no measurement worker starts. The pilot
and main modes validate their separate configurations and preserve separate runs.

```sh
.venv/bin/python studies/01-strategy-loop/analysis/run.py --verify \
  --config studies/01-strategy-loop/configs/main.json --output build/strategy-main-verify
.venv/bin/python studies/01-strategy-loop/analysis/run.py --main \
  --verified build/strategy-main-verify --output build/strategy-main
MPLCONFIGDIR=build/matplotlib XDG_CACHE_HOME=build/cache .venv/bin/python \
  studies/01-strategy-loop/analysis/plot.py --main --input build/strategy-main \
  --output build/strategy-main-figures
```

The quiet gate records a low-load entry interval, not CPU isolation. Retain later
load changes and qualify interpretation accordingly. An old verification fails
if implementation/configuration source changes; build and verify the current
checkout before a new run.

## Figures

```sh
MPLCONFIGDIR=build/matplotlib XDG_CACHE_HOME=build/cache .venv/bin/python \
  studies/01-strategy-loop/analysis/plot.py --input build/strategy-pilot \
  --output build/strategy-pilot-figures
```

The plotter refuses an incomplete matrix or mismatched input, summary or raw
worker record. It produces a clearly labelled synthetic account heatmap, a
four-panel timing plot retaining every process observation with separate medians
for each seed, and a complete-cost view. Each complete-cost stacked bar comes
from one actual run nearest the group's median total, breaking ties by run ID;
all four totals also appear. No independently selected stage medians are added.
Warm paper, upright Georgia, blue and red follow the publication style file.

The `previews/` directory contains teaching diagrams and mock data. The
commands here generate figures from the saved verification or timing records.

The account illustration can also be rendered from completed untimed verification,
without fabricating timing values:

```sh
MPLCONFIGDIR=build/matplotlib XDG_CACHE_HOME=build/cache .venv/bin/python \
  studies/01-strategy-loop/analysis/plot.py --example --input build/strategy-verify \
  --output build/strategy-account-figure
```

## Historical QQQ reproduction

The article uses split-adjusted QQQ minute bars from Alpaca SIP. Follow the
[download guide](tools/alpaca/README.md) to get the data. The
[historical plan](historical-plan.md) explains how the three price windows
were picked. Download, normalize and check the data before starting the timer.

Normalize the export and compute the position-activity summaries:

```sh
.venv/bin/python studies/01-strategy-loop/analysis/historical.py \
  --source local/data/alpaca/QQQ_1Min_2023-01-01_2026-01-01_sip_split \
  --output local/data/strategy-loop/qqq-rth-20261117

.venv/bin/python studies/01-strategy-loop/analysis/profiles.py \
  --datasets local/data/strategy-loop/qqq-rth-20261117/manifest.json \
  --output local/evidence/strategy-loop/historical-20261117/profiles
```

Use fresh output directories. Both historical configs point to the input
manifest by hash. A new download can produce a different manifest even when
prices agree. Review the inputs and copy the configs with the new hash before
starting a separate run. Keep the original configs with their original results.

Correctness commands, with the optional real-data excerpts enabled:

```sh
cmake --preset debug
cmake --build --preset debug
STRATEGY_HISTORICAL_CSV="$PWD/local/data/strategy-loop/qqq-rth-20261117/qqq-jump-n4096.csv" \
  ctest --preset debug
```

Build release once, then run the untimed check. Use the same verification
directory for both timing runs. The main matrix covers all 48 verification
cases and includes every case the pilot needs.

```sh
cmake --preset release
cmake --build --preset release

study=studies/01-strategy-loop
python=.venv/bin/python
main_config="$study/configs/historical-main.json"
pilot_config="$study/configs/historical-pilot.json"
datasets=local/data/strategy-loop/qqq-rth-20261117/manifest.json

"$python" "$study/analysis/run.py" --verify --config "$main_config" \
  --datasets "$datasets" --output build/qqq-verify
"$python" "$study/analysis/run.py" --pilot --config "$pilot_config" \
  --verified build/qqq-verify --output build/qqq-pilot
"$python" "$study/analysis/run.py" --main --config "$main_config" \
  --verified build/qqq-verify --output build/qqq-main
```

Use the config paths from your new input review if the manifest hash changed.
Run the pilot and main sequentially. Both wait for a full minute below the
load limit and stop if power changes. If the source, config or binary changes,
repeat verification before timing. The original run also recorded process
activity every five seconds through a separate monitor and ran on AC.

To regenerate the checked historical figures from the retained archive:

```sh
MPLCONFIGDIR=build/matplotlib XDG_CACHE_HOME=build/cache .venv/bin/python \
  studies/01-strategy-loop/analysis/plot_historical.py \
  --run local/evidence/strategy-loop/historical-20261117/main/campaign \
  --profiles local/evidence/strategy-loop/historical-20261117/profiles \
  --output build/historical-figures
```

The plotter verifies raw worker identities/order, stdout and summary hashes,
independent references, input/source/build snapshots, interval arithmetic and
power consistency. It exports all observations, group summaries, paired ratios
and activity descriptors. The current curated copies are in `results/` and
`figures/`. No measurement is required merely to regenerate these plots.
