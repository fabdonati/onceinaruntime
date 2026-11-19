# Strategy-loop findings

## Static mechanism analysis, 17 November 2026

The selected mechanism follow-up reached its bounded static stopping point.
The diagnostic GCC compile produces an object byte-identical to the measured
release object. A hash-pinned inspector follows reviewed steady cash/long paths
in each of the four routes and retains every instruction and memory operand.

For a nonfinal, unchanged-position update, strategy-first has no explicit account
loads or stores inside the reviewed iteration: the 56-byte account is loaded
before its history and stored afterwards. Event-first reads 32 B of account
fields (cash, shares, peak and drawdown) and writes 16 B (peak and drawdown).
Those are architectural operand bytes, not measured DRAM traffic or cache misses.
Trade, startup, liquidation and outer-loop boundary paths are excluded.

Steady cash/long path counts are respectively 18/20 instructions for
strategy/history, 20/23 for strategy/snapshot, and 29/30 for both event-first
layouts. These are path-specific static counts, not retired counters or cycle
costs. Every reviewed path includes a scalar division for drawdown. All read
two EMA values; coordinate spacing and generated address instructions differ.
The [detailed report](mechanism-check.md) gives exact offsets and assumptions.

The supported explanation now includes state-register use, loads/stores,
addressing and branch structure. It does not assign shares of runtime to them.
In particular, the historical event/snapshot median was lower despite more
instructions on these steady paths, so instruction count alone does not settle
the measured reversal. Data reuse and cache behaviour remain runtime hypotheses.

`xctrace` is only a system shim in the checked setup; it reports that full Xcode
is required. Command Line Tools is active, Spotlight finds no indexed Xcode
bundle and `perf` is absent. Hardware counters were not collected. The bounded
feasibility stop therefore applies; no new toolchain or timing campaign was run.

Debug configure/build/CTest passed all six entries, including 33 strategy tests
and real-data excerpts. No C++ implementation changed or new sanitizer run was
needed. Raw compiler/tooling records and disassembly remain under
`local/evidence/strategy-loop/mechanism-20261117/`. The public
[path record](results/mechanism-paths.json) and
[illustration](figures/09-account-state-mechanism.png) support the draft addition.
Next: author review; quantitative attribution needs a usable counter profiler.

## Bounded mdspan check, 17 November 2026

The author selected a comparison between the existing dynamic-extent mdspan
access and the corresponding manual pointer offsets, preserving the complete
kernel, layouts, state lifetime and compiler settings. The implementation builds
separate default/manual binaries from the same source; there is no new access-mode
runtime branch or manual-only aliasing/extent advantage.

Both complete non-diagnostic replay functions contain **645 static instructions**,
including all four traversal/layout routes. Addresses and mnemonic counts match.
Eleven encodings differ: four floating multiply operand swaps, three integer
comparison operand swaps immediately consumed by equality/inequality branches,
and two reversed floating comparisons with corresponding select conditions.
All other instructions, including address calculations, loads, stores and branch
targets, match exactly. This is static code inspection, not a retired-instruction
counter measurement. The mdspan object is byte-identical to the original measured
release object; the manual object differs as described.

The supported claim is **manual indexing saves no instructions in this GCC 16.2
replay build**. The access abstraction leaves no additional address or memory
operations here. This is scoped to the actual default accessor, mappings,
dynamic extents and kernel; it does not establish universal zero overhead.

Debug and ASan/UBSan configure/build/CTest all passed, with real-data excerpts
enabled. Both access variants match the independent oracle in trace and no-trace
boundary fixtures. The fixed directional QQQ workload (N=32,768, W=48, K=1,128)
passed all eight full-size untimed checks and all 32 paired pilot observations.
Every account summary was byte-identical between C++ variants and matched the
retained independent ledger within its documented tolerance.

The pilot ran on AC after 120.243 seconds establishing the quiet-entry gate;
total elapsed time was 124.765 seconds. Measurement load rose from 3.286 to 9.669.
Four pairs per route and uncontrolled background work cannot establish a precise
timing-overhead percentage. No samples were dropped or replaced, and no repeat
campaign was selected to obtain a cleaner-looking result. Prepared intervals
below include replay and required summary construction:

| Traversal / storage | mdspan median ms (min–max) | Manual median ms (min–max) | Median paired mdspan/manual ratio |
| --- | ---: | ---: | ---: |
| Strategy / history | 32.478 (32.102–32.914) | 32.0615 (31.922–33.681) | 1.00374 |
| Event / history | 80.9485 (80.012–83.660) | 82.011 (80.475–84.275) | 0.99237 |
| Strategy / snapshot | 61.197 (57.495–65.079) | 58.3785 (57.672–61.695) | 1.02392 |
| Event / snapshot | 44.332 (43.319–46.258) | 43.5155 (43.478–44.755) | 1.01949 |

These are descriptive pilot values, not proof of equivalence, significance or
an abstraction-caused speed difference. Minimum positive consecutive clock-read
delta was 1 microsecond; maximum observed worker RSS was 36,847,616 bytes.

An earlier attempt passed eight untimed workers but ran zero timing workers:
the power guard rejected macOS's `finishing charge` status despite AC power.
That attempt is retained. The parser was fixed and regression-tested before the
separate successful campaign. No system settings or power sources were changed.

The [protocol](mdspan-check.md), [curated code/timing evidence](results/mdspan-summary.json)
and [individual pilot observations](results/mdspan-pilot-observations.csv) record
the details. Raw commands, disassembly, source/build snapshots and all outputs
remain in `local/evidence/strategy-loop/mdspan-20261117/`. The original historical
campaign is unchanged, and its plots do not need rerunning. This follow-up's
stopping condition is met; next is author review of the short article addition.

## Historical QQQ extension, 17 November 2026

The author supplied an Alpaca SIP export of split-adjusted one-minute QQQ bars
for 2023–2025. Both merged hashes and all 36 monthly CSV/response hashes match;
the 640,204-row open/close projection agrees exactly with the full CSV. Prices
are finite, positive and consistent with OHLC bounds; timestamps are unique,
ordered, minute-aligned and agree with the UTC column. The bounded exchange
calendar accepts 291,840 regular-session minutes across 752 sessions, with none
missing. Eight early closes and the exceptional 9 January 2025 closure are
included. No prices were filled or original files changed.

Eight non-overlapping 32,768-bar candidates were ranked by the predeclared
price-only rule; the remaining 29,696 bars are an incomplete tail. Long windows:

| Profile | Block (zero-based) | First included UTC bar | Last included UTC bar |
| --- | ---: | --- | --- |
| Largest gap | 4 | 2024-05-07 13:32 | 2024-09-06 16:39 |
| Directional | 7 | 2025-05-12 16:26 | 2025-09-11 19:33 |
| Low directionality | 6 | 2025-01-08 17:18 | 2025-05-12 16:25 |

Each supplies the fixed nested 4,096-bar crop. The largest consecutive included
close gap spans 2–5 August 2024; its two bars agree with the retained raw provider
response, and adjacent extended-session/opening bars are consistent. The
provider applied split adjustment. The reviewed [QQQ fiscal-2024 statements](https://www.sec.gov/Archives/edgar/data/1067839/000119312525013448/d902673d485bpos.htm)
did not identify a QQQ split at this boundary; this review is not a separate
corporate-action-feed audit. The gap is an input descriptor, not a claim about
the cause of a market move. The exact check is retained in `jump-source-check.json`.

`cmake --preset debug`, `cmake --build --preset debug` and `ctest --preset debug`
passed all six CTest entries. The Python suite contains 30 tests; with the local
historical fixture enabled, both real excerpts pass every feature, trace and
ordered-summary check across all four variants, including an overnight boundary.
No C++ code changed, so the existing sanitizer-tested engine and release binary
were reused. The binary SHA-256 remains
`8b964006f87411ceb5bb814945f96942e8ea885e85c85990a2c92486d47f2057`.
A separate independent ledger gate then passed all **48 untimed workers**.

The **48-observation pilot** passed after 150.289 seconds waiting for quiet;
total elapsed time was 154.870 seconds. The separately frozen **384-observation
main campaign** passed after 60.110 seconds waiting for quiet; total time was
79.575 seconds, approximately 19.5 seconds after entry. Main measurement load
stayed between **1.977 and 2.140**, ending at 2.038. All sampled power reports
were AC; battery permission was available but unused. CPU placement, frequency
and background processes remained uncontrolled. Five-second read-only process
sampling adds uncontrolled monitoring overhead.

All worker outputs matched the independent reference, and matching C++ variants
and repetitions were byte-identical. Final integrity passed. Main evidence was
about 31.0 MB; maximum worker RSS was 37,044,224 bytes. Candidate order used the
balanced four-row design, while profile/N/K blocks rotated between repetitions.
No observation was replaced or dropped. All 1,346 files copied from temporary
pilot/main output directories were hash-verified after measurements.

The storage-dependent median ordering repeated in all **12 historical N/K/profile
cells**: strategy-first within history storage, event-first within snapshot
storage, strategy-first/history lowest overall. Across the twelve cells, medians
of eight paired `T_strategy/T_event` ratios ranged from **0.359–0.660** for history
storage and **1.219–1.547** for snapshot storage. These are descriptive matched
ratios, not confidence intervals or ratios pooled across power/input conditions.

For the preselected directional profile at N=32,768, K=1,128:

| Traversal / storage | Prepared median ms | Observed range ms | Complete median ms |
| --- | ---: | ---: | ---: |
| Strategy / history | 32.079 | 31.876–33.055 | 35.8035 |
| Event / history | 81.672 | 79.672–83.838 | 85.400 |
| Strategy / snapshot | 57.7455 | 57.064–63.720 | 64.0505 |
| Event / snapshot | 43.499 | 43.273–44.393 | 50.067 |

At K=64 on the same long profile, strategy/history versus event/snapshot prepared
medians were 2.629 and 2.967 ms; complete medians were 6.3265 and 9.3445 ms.
Complete totals are measured intervals, not sums of separately aggregated stages.

The activity descriptors qualify how much input diversity was achieved. At
N=32,768 and K=1,128, opening changes per 1,000 updates were 20.34 (gap), 21.16
(directional), 20.30 (low directionality). Long fractions were 54.6%, 58.1%, 52.6%;
pooled completed-long-spell medians were 25, 23, 24 bars. Initial entries count;
final liquidation does not; ending spells are separately censored. All twelve
activity cells, quartiles and transition blocks are retained. These paths give
only modest activity variation; they do not establish three distinct branch or
cache regimes. The K=64 lexicographic prefix is more concentrated in fast spans
and has higher switching rates, so changing K changes configuration population.

The original data and all raw evidence stay ignored under
`local/data/` and `local/evidence/strategy-loop/historical-20261117/`. The latter
contains verification, pilot/main campaigns, profile reports, monitoring, exact
commands, archive audit and source snapshots at revision `c71d6dc` with the
recorded dirty tree. The historical plotter was added after timing; its hash is
recorded with its derived exports. It independently rechecks raw worker records,
ordered summaries and input/build integrity before drawing figures.

The current article uses the new historical figures. Earlier synthetic, AC and
battery campaigns remain separately retained; none were pooled. Next: author
review of the explanation and figures. No new benchmark is needed for this
bounded extension. Historical minute-bar replay does not establish live HFT
latency, a cache-miss mechanism, abstraction overhead or executable profitability.

## Completed battery reproduction, 17 November 2026

The author explicitly authorized battery operation after the held attempt.
The runner now exposes `--allow-battery`; AC remains the default. Failed or
unknown power queries still fail the gate. The manifest records the override
and actual power reports. Debug configure/build and all six CTest entries passed,
including a regression check for the override. No C++ implementation changed;
the release binary hash matches earlier runs. A fresh **72-worker untimed
verification** passed for the updated runner before timing.

The same 576-observation matrix, eight repetitions, seeds, workloads, execution
order, quiet interval and resource caps were retained. Evidence and five-second
process monitoring were written to temporary local storage, then copied to
`local/evidence/strategy-loop/battery-20261117/` after completion. All 1,993 copied
files were hash-verified. The archive retains `campaign/`, `verification/`, exact
commands, the monitor script/log and `comparison.json`. Original manifests and
paths were not rewritten; no observation was removed or replaced.

All **576 observations passed output checks and final integrity**. The plot
loader independently audited raw observations and summary hashes. Quiet entry
took 60.085 seconds; total campaign time was 88.523 seconds (about 28.4 seconds
after the gate). All measurement power samples reported battery operation at
99%. Recorded measurement load stayed between **2.062 and 2.269**, ending at
2.147. Six process snapshots during measurement showed modest background work
rather than the prior file-service spike; this does not prove full isolation.

The ordering repeated in all 18 N/K/seed cells: strategy-first wins within
history storage, event-first within snapshot storage, and strategy-first/history
has the lowest median overall. At N=32,768, K=1,128 and seed 11:

| Traversal / storage | Battery prepared median, ms |
| --- | ---: |
| Strategy / history | 31.310 |
| Event / history | 79.989 |
| Strategy / snapshot | 56.2005 |
| Event / snapshot | 42.509 |

Across 72 matched candidate/cell medians, battery/latest-AC ratios ranged from
0.881 to 1.104, with median 0.988. Do not attribute these differences to power
source: output location, power and background conditions changed together.
This is a useful separate reproduction of the ordering, not a controlled study
of power modes or file-service interference. Keep AC and battery distributions
separate. Next: reconcile the article/charts with the explicitly recorded
conditions; more repetitions are not needed merely to repeat the ordering.

## Additional attempt held on battery, 17 November 2026

An additional requested reproduction retained the same 576-observation matrix;
increasing repetitions would not resolve the known background-load limitation.
Evidence output was directed to temporary local storage to explore possible
file-service interference without changing the executable or workload. The
source and binary verification matched, but the runner detected **Battery Power**
(100%, discharging) at entry, with load 2.383. It returned `not_started` and
collected **zero timing observations**. No temporary-output timing result exists.
The complete held-run record was copied to
`local/evidence/strategy-loop/rerun-held-battery-20261117/`, with every copied file
hash checked. Next: reconnect AC power before another attempt. Earlier completed
campaigns and observations remain unchanged.

## Reproduction run, 17 November 2026

The same frozen 576-observation main matrix was run once more after an author
requested CPU check. Source and release executable hashes exactly matched the
completed 72-worker verification from 16 November; no rebuild or new correctness
implementation was needed. Preview-only edits were present in the working tree.
The runner retained the revision, dirty state, source archive, exact commands,
inputs, ordered summaries and all individual observations separately from the
earlier campaign. No observations were removed or replaced.

The quiet entry interval passed after 165.273 seconds. The complete campaign took
196.817 seconds including that wait (about 31.5 seconds afterwards). All **576
output checks passed**, final integrity passed, and the plot loader independently
audited the complete raw observation matrix and summary hashes. Original records
are in `local/evidence/strategy-loop/main-20261117/`; the separately retained
monitor command, script, stdout/stderr and five-second process samples are in
`local/evidence/strategy-loop/rerun-control-20261117/`.

The ordering repeated in all 18 N/K/seed cells: strategy-first was faster within
history storage, event-first was faster within snapshot storage, and
strategy-first/history had the lowest median of all four. Across all 72 matched
candidate/cell medians, rerun/previous timing ratios ranged from 0.932 to 1.095,
with median 1.006. These are descriptive comparisons, not confidence intervals.

At N=32,768, K=1,128 and seed 11:

| Traversal / storage | Previous prepared median, ms | Rerun prepared median, ms |
| --- | ---: | ---: |
| Strategy / history | 31.747 | 31.621 |
| Event / history | 82.5595 | 81.7465 |
| Strategy / snapshot | 58.553 | 57.6745 |
| Event / snapshot | 42.5405 | 42.717 |

**The entry check again did not ensure quiet measurement.** Load was 3.305 at
measurement entry and reached 29.602 by the final campaign sample. AC remained
stable. Process snapshots during measurement showed `fileproviderd` reaching
104.5% CPU (roughly one core), Spotlight and thumbnail activity, and a separate
Python process reaching 70.7%. These are sampled process CPU readings; they do
not identify the full cause of load or quantify interference in each timing.
The five-second monitor itself adds uncontrolled overhead. Its final sample,
after campaign completion, reached load 34.438 and is not a measured-phase peak.

The repeated ordering supports the bounded result, but this is still not an
isolated-machine performance estimate. A possible contributor is file-service
activity associated with the many evidence files; that mechanism has not been
established. Before any further reproduction, investigate output placement and
background work rather than repeating unchanged runs. No system settings or
unrelated processes were changed. Both campaigns and the current article figures
are retained; new figure exports remain separate pending editorial review.

## Executed: layout example, 15 November 2026

The existing GCC 16.2/libstdc++ route compiled the actual `std::mdspan` view in
C++23 mode. The compiler reported `__cplusplus=202302` and
`__cpp_lib_mdspan=202207`. Ordinary and ASan/UBSan executions passed.

The example independently checks six logical values, both mappings' strides,
zero/one-element boundaries, and a counterexample where viewing a history-ordered
buffer as snapshot-ordered reads a different value. This establishes the local
API route and illustrates that a mapping change does not rearrange storage.

Exact commands, source hash, revision/dirty state and outputs are retained in
`local/evidence/strategy-loop/preflight-20261115/report.json`, excluded from Git.
The runnable source is [examples/layout.cpp](examples/layout.cpp).

Root debug configure/build/CTest and root sanitizer configure/build/CTest also
passed after integration: five CTest entries each, including the existing barrier
and precision checks, twenty Python analysis tests, and the new layout example.

## Executed: accounting and replay, 15–16 November 2026

The [engine](src/replay.cpp) implements strategy-first/event-first traversal,
each with history/snapshot feature storage. All routes share the state transition
and required summaries. The [Python reference](analysis/reference.py) records a
separate transaction ledger and equity history. It derives fees, turnover and
trade counts from that ledger rather than calling the C++ implementation.

Root debug, sanitizer and release configure/build/CTest passed: six CTest entries
per build, including sixteen strategy accounting/runner tests and all existing
barrier checks. No new timing observation was made by those tests.

| Check | Observed outcome |
| --- | --- |
| Hand-calculated EMA values and fractional fee arithmetic | Passed, including rational expected values. |
| Next-open execution and overnight gap | Passed; mutating the current close leaves the current opening decision unchanged. |
| Flat/equal averages, no trades, common warm-up, empty replay/configurations | Passed. Empty replay requires explicit correctness mode. |
| Final liquidation | Passed; exit fees replace the final equity mark and affect drawdown. |
| Invalid prices, spans, timestamps, fees and capital | Rejected. |
| Full small-fixture diagnostic output | Every feature and every trace/summary field checked against the reference. |
| C++ route agreement | Ordered feature/trace/summary CSVs byte-identical across all four variants. No-trace summaries also agree exactly. |
| Floating-point reference agreement | Exact decisions and trade counts; monetary/statistic values within rel_tol 2e-12 and abs_tol 1e-9. EMA values exact. |
| ASan/UBSan | All strategy checks passed; no diagnostic reported. |

The [five-bar example](examples/account.md) produces final cash
989.80201979802018, two trading events and max close-to-close drawdown
0.029508823529411754. These are arithmetic results on invented prices, not
observed investment returns. Its fee-free version reproduces the manuscript's
1,000 -> 1,020 -> 990 walkthrough.

Build commands/stdout/stderr are retained under
`local/evidence/strategy-loop/implementation-20261115/`. The final nine build/test
commands are in `final-build-commands.json`. Checks do not establish correctness
for shared capital, competing fills or other excluded models.

## Executed: untimed scale gate

The frozen matrix uses 4,096 and 32,768 synthetic bars, 48 EMA spans (2..96,
step 2), seeds 11 and 29, and 64/256/1,128 nested configurations. All four routes
passed on all combinations: **48 untimed C++ workers**. Each result was compared
with the ordered independent Python summaries; C++ summaries were byte-identical
within each input/count group. The largest absolute reference difference across
all numeric summary fields was approximately 1.08e-10. The tolerance applies to
each field separately; this aggregate maximum is not an error bound for finance.

Every history has its own generated CSV. The short input was not repeated to
manufacture the longer one. Every selected K references all 48 windows, though
pair frequencies change with K. Full diagnostic traces were checked on the small
fixtures; the larger gate checks summaries, not all large per-bar traces.

Two scale verifications were retained. The second,
`local/evidence/strategy-loop/verify-20261116/`, refreshes the source snapshot after
the figure tool gained an untimed example mode. Each includes actual source,
binary, build flags, input/reference files, hashes, commands and raw observations.
The code was based on revision `03efc2c263aefc4a4582cd5e4e89e352eb395f27` with
recorded uncommitted implementation changes; the source archive identifies what
was actually checked. Do not use that base revision alone to reproduce the engine.

## Executed: compiler inspection

GCC 16.2 with `-O3 -DNDEBUG -std=c++23 -fno-fast-math -ffp-contract=off` reports
zero vectorized loops in the replay function. Its reports cite unsupported
control flow in the loop bodies and also identify some vectorized basic-block
operations. Therefore this implementation does not establish SIMD across
strategy iterations; it also would be inaccurate to say the object contains no
vector operations.

The diagnostic compile produced an object byte-identical to the release build's
object. The exact commands, hashes, assembly and report are retained under
`local/evidence/strategy-loop/compiler-20261115/`. This is compiler evidence,
not a measured explanation of runtime or cache behavior.

## Figures and timing status

The [account heatmap](figures/01-synthetic-accounts.png) uses checked outputs from
the 32,768-bar synthetic seed-11 input, all 1,128 configurations. Its
[input table](figures/accounts.csv) and [figure record](figures/README.md) identify
that relationship. Both the chart and caption explicitly identify invented
prices. The traversal diagram is a schematic. Older return/timing/stage previews
under `previews/` remain fabricated design values.

The timing pilot is frozen at 192 fresh-process observations and a 15-minute cap.
The first launch on 16 November local time was held before any worker ran:
one-minute load was 8.596 on eight logical CPUs, exceeding the declared limit of
4. Stable AC power was present. The preserved manifest is
`local/evidence/strategy-loop/pilot-20261116/manifest.json`, status `not_started`,
zero observations. No failed or slow measurement was discarded or replaced.

## Completed pilot

When the gate subsequently passed, a new campaign completed all 192 observations
without replacement: `local/evidence/strategy-loop/pilot-20261116-started/`.
Every ordered output passed the same independent checks. The campaign took
9.385 seconds and retained approximately 14.6 MB. The largest observed worker
RSS was 36,913,152 bytes. Prepared intervals ranged from 0.316 to 84.281 ms.

The positive timer-read delta was 1 microsecond; 9,960 of 10,000 consecutive
read pairs were equal. Timer resolution is not the timer-call cost. The machine
is an Apple M3 with 16 GiB RAM and eight logical CPUs, confirmed by a read-only
follow-up after the sandbox denied the in-run query. The original query failure
is preserved. GCC and flags are recorded above and in each campaign.

Within every tested N/K/seed cell, strategy-first had lower median prepared cost
on history storage; event-first had lower median prepared cost on snapshot
storage. Strategy-first/history was the lowest of the four medians at every
cell. This is an observed ordering in the pilot, not an explanation of the
hardware mechanism or a general speedup claim.

Entry load was 3.954, below the limit of 4, but later load reached 12.631. AC
power was stable at all fifty recorded samples. That variation and four samples
per cell keep the result exploratory. See the [complete pilot tables and
conditions](results/README.md). The shorter sweep's complete-cost chart shows
why preparation matters even when the same kernel ordering holds.

## Confirmation campaign

A separate [main plan](measurement-plan.md) was frozen after inspecting the pilot:
same N/K/W and model, seeds 11/29/47, eight observations per candidate/cell, 576
workers. Its independent gate passed all 72 untimed workers before timing;
records are in `local/evidence/strategy-loop/main-verify-20261116/`.
Debug, sanitizer and release checks passed again after adding the main mode.

The main runner required a full minute of low recorded load before starting,
with a ten-minute entry-wait cap inside its fifteen-minute total cap. It waited
240.388 seconds; the final five entry loads were 3.589, 3.372, 2.914, 2.637 and
2.274, all below the limit of 4. It then completed **576 observations**, all with
passed ordered-output checks, in approximately 32 seconds. Total campaign time
including the wait was 272.087 seconds. No timing observation was replaced.

The manifest is `local/evidence/strategy-loop/main-20261116/manifest.json`, status
`complete`, final integrity `passed`. Evidence occupies approximately 38.2 MB;
maximum worker RSS was 36,880,384 bytes. Prepared intervals ranged from 0.306
to 105.173 ms. The clock's minimum positive consecutive-read delta was again
1 microsecond; 9,975 of 10,000 pairs were equal. AC power remained stable in
all 163 recorded environment samples, including the entry wait.

**Load rose during the measured phase, reaching and ending at 36.116.** The
quiet entry condition was met, but this was not a continuously isolated or idle
host. Preserve that distinction. The full observation distributions are retained;
do not turn the following medians into a stable production speedup estimate.

The pilot's ordering repeated in all 18 N/K/seed cells. Within history storage,
strategy-first had the lower median prepared cost; within snapshot storage,
event-first had the lower median. Strategy-first/history had the lowest median
of the four candidates at every cell. The mechanism behind that ordering remains
unmeasured. Adding seeds also does not establish behavior across real markets.

At N=32,768, K=1,128 and seed 11, the eight-observation prepared medians were:

| Traversal / storage | Prepared ms | ns / strategy-bar | Observed prepared range, ms |
| --- | ---: | ---: | ---: |
| Strategy / history | 31.747 | 0.8614 | 31.300–33.025 |
| Event / history | 82.5595 | 2.2402 | 79.542–100.806 |
| Strategy / snapshot | 58.553 | 1.5888 | 56.825–59.984 |
| Event / snapshot | 42.5405 | 1.1543 | 42.417–43.223 |

At K=64 on the same N/seed, strategy/history versus event/snapshot prepared
medians were 2.618 and 2.9325 ms; complete computation medians were 6.378 and
9.9355 ms. This motivates retaining the complete-cost figure. These total medians
are measured totals, not sums of independent stage medians. Every group and
individual observation is available in [results](results/README.md).

The main source/binary snapshots identify the actual executed files. Changes
between the pilot and main affected the runner, plotting support, configuration
and its tests; the C++ replay implementation and release executable were unchanged.

## Limits

The earlier synthetic campaigns do not themselves establish historical-market
behaviour. The historical extension above adds that bounded input coverage, but
no causal cache explanation, measured abstraction overhead or production-HFT
latency claim. The [run guide](benchmark.md)
contains exact commands. A historical-market illustration can be chosen
separately; the current performance investigation identifies its synthetic inputs
and simplified account model throughout.
