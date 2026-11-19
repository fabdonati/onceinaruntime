# Float/double comparison

The original double implementation remains in `src/`. This extension adds a
separate float library, worker, correctness suite and bounded pilot runner.
No speedup or acceptable numerical-error threshold is assumed.

## Numerical contract

| Variant | Stored multipliers | Path/discount/payoff arithmetic | Ordered reduction |
| --- | --- | --- | --- |
| FP64 | double | original double implementation | double |
| FP32 | float | float | double |

The current GCC/ARM build reports two native double lanes and four native float
lanes. The worker records the actual widths; another target can differ. Canonical
GBM multipliers are generated once in FP64 using the existing generator and then
rounded once to FP32. Each layout uses those same values. This changes storage,
precision and pack width together, so the runtime difference cannot be attributed
solely to wider packs. The generator itself remains double precision.

All three methods must exactly match an independent oracle of their own
precision, for every ordered payoff, stopping date and knock-out flag. Numerical
differences **between** precisions are reported, not treated as implementation
failures. Literal and near-barrier counterexamples test the distinction.

The accuracy report includes knock-out changes in both directions, stopping-date
changes, zero-payoff changes, maximum/RMS payoff error and signed price change.
It counts each seed/barrier once, irrespective of repeated timing processes.
An additional untimed FP64 reference uses the rounded FP32 inputs widened back to
FP64. This helps inspect input quantisation versus remaining arithmetic changes;
early-exit interactions prevent treating them as independent causal effects.
FP64 is a numerical reference, not a known exact option price.

## Build and verify

Run from the repository root; use the Python environment with NumPy/Matplotlib.

```sh
cmake --preset precision-debug
cmake --build --preset precision-debug
ctest --preset precision-debug
cmake --preset precision-sanitize
cmake --build --preset precision-sanitize
ctest --preset precision-sanitize
cmake --preset precision-release
cmake --build --preset precision-release
ctest --preset precision-release
.venv/bin/python -m unittest discover -s studies/02-barrier-options/tests -p 'test_*.py'
.venv/bin/python studies/02-barrier-options/analysis/run_precision.py \
  --smoke --output build/precision-smoke
.venv/bin/python studies/02-barrier-options/analysis/run_precision.py \
  --verify --output build/precision-verification
```

Smoke and verification are untimed and need no quiet-window gate. The complete
verification checks 108 precision/method/layout/seed/barrier configurations.
Use fresh output directory names: existing directories are refused.

## Run the timing pilot

Keep the machine plugged in and quiet. Compile and run correctness checks before
starting; avoid simultaneous benchmarks or plotting. No system settings are
changed. First check the release artifacts, AC state and starting load:

```sh
.venv/bin/python studies/02-barrier-options/analysis/run_precision.py --check
.venv/bin/python studies/02-barrier-options/analysis/run_precision.py \
  --run --output build/precision-pilot
```

The frozen pilot is 8192 paths × 252 dates, three seeds, three barriers, two
layouts, two precisions and three methods. Six cyclic execution-order rotations
give 648 fresh-process observations, with one warm-up each. Every candidate
occupies every order position once per seed/barrier/layout. The 30-minute limit is
a ceiling, not a measured duration estimate. There are separate 1-GiB evidence and
conservative parent-plus-child peak-RSS caps.

Prepared timing includes path calculation, every payoff write and ordered FP64
aggregation. Generation, casts, layout conversion, validation, diagnostics and
file I/O are outside the interval. Their input sizes/hashes remain recorded;
these results cannot establish a complete-valuation speedup.

The runner refuses an ineligible start and samples power/load throughout. Later
load changes remain in the record. It stops on failure, incorrect outputs,
nonfinite durations, power instability or resource limits, preserving partial
results. No slow observations are replaced and no automatic repeats are added.
Shared lock files prevent overlap with the normal original main-runner builds.
Collect a larger campaign only after assessing this pilot and defining its budget.

## Analyse

After the run completes, this command validates retained logs and path outputs,
then writes matched timing tables, per-seed accuracy tables and two PNG/SVG views:

```sh
MPLCONFIGDIR=build/matplotlib .venv/bin/python \
  studies/02-barrier-options/analysis/analyze_precision.py \
  --input build/precision-pilot --output build/precision-pilot-analysis
```

The accuracy analysis can also consume an untimed smoke/verification directory;
it then produces no runtime plot or timing ratios. Timing effects are
`100 * (FP32 time / FP64 time - 1)` matched within method/seed/repeat/layout/barrier.
Observed ranges are descriptive, not confidence intervals. Three input seeds
with repeated process timings do not establish tail latency or production
pricing accuracy. Individual observations and all path outputs remain available
for inspecting numerical differences without hiding cancellation in an average.
