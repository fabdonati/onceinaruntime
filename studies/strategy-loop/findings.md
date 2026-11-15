# Strategy-loop findings

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

There is no historical-market result, causal cache explanation, measured
abstraction overhead or production-HFT latency claim. The [run guide](benchmark.md)
contains exact commands. A historical-market illustration can be chosen
separately; the current performance investigation identifies its synthetic inputs
and simplified account model throughout.
