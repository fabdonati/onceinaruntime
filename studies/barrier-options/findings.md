# Findings and limits

Status: original double main campaign and descriptive analysis complete;
float/double implementation checked, precision timing pilot not run.
See [README](README.md) for the current next step and [article](article.md) for
the preliminary manuscript. Historical chronological logs remain in local evidence
and the verified pre-reorganization archive rather than being maintained here.

## Scope and correctness

Scalar early exit, fixed native SIMD and refill return identical ordered payoffs,
lifetimes and knock-out flags under both input layouts. Literal/Decimal fixtures,
debug and sanitizer checks and 138 independent verification cases passed before
the original main. Its three seeds, three barriers, two layouts, three methods
and six balanced orders produced 324 prepared and 324 complete observations in
648 sequential pricing processes. Every required output passed its oracle audit.

The original main took 618.41 seconds and retained 622959148 bytes. No failed,
excluded or replacement measured observation occurred. Earlier environment holds
had no pricing observations and remain separately identified. Measured sources,
flags, executables, raw logs and individual observations were retained.

AC charging was reported in all 114 environment samples. Load was 3.68 at
observation entry, reached 16.56 and ended at 10.14; all samples were retained.
Process inspection was denied and thermal queries failed. Quiet execution,
core placement, stable frequency and thermal control were not established.

## Main descriptive analysis, 14 November

Prepared-input medians in milliseconds, each pooling 18 observations (three seeds × six fresh-process repeats):

| Input layout | Barrier | Scalar | Fixed SIMD | Refill SIMD |
| --- | ---: | ---: | ---: | ---: |
| Path-major | 105 | 15.66 | 17.97 | 20.67 |
| Path-major | 120 | 27.93 | 20.63 | 20.00 |
| Path-major | 150 | 33.82 | 20.65 | 22.34 |
| Step-major | 105 | 21.73 | 22.67 | 21.47 |
| Step-major | 120 | 38.98 | 33.02 | 35.53 |
| Step-major | 150 | 43.55 | 30.90 | 40.65 |

These are pooled absolute-time medians, not medians of paired speedups. All individual observations, full observed ranges, per-seed summaries and 108 matched fixed/refill comparisons are retained separately. The 163.41 ms scalar observation at step-major barrier 105 is retained in the table and chronological diagnostic. Within-seed/case six-repeat `(maximum−minimum)/median` had median 26.82% and maximum 555.49% for prepared input, and median 17.61% and maximum 48.19% for complete valuation. Three seeds with repeated process timings are not eighteen independent input populations.

Fixed-group logical occupancy pooled across unique seeds was approximately 64.8%, 86.7% and 99.1% at barriers 105, 120 and 150. Refill exceeded 99.99% in each case. These counters are consistent across layouts and timing repetitions, and useful work equals the reference lifetimes. In step-major barrier 150, every one of the eighteen refill observations exceeded every fixed observation: refill's minimum was 36.09 ms and fixed's maximum 34.34 ms. Median matched change `100 × (refill/fixed − 1)` was +32.75% there. This establishes an observed ordering within this campaign, not a general speedup or hardware cause.

The other cases include overlapping timings and mixed matched differences. For example, path-major barrier 120 had median matched refill change −2.30%, with observed matched changes from −44.73% to +53.99%. Such differences do not support a precise crossover claim. The low-barrier pilot pattern also did not persist unchanged at the larger main workload. Workload size and desktop conditions both changed; these observations do not isolate why.

For the complete pipeline, phase cards pool all three barriers equally, giving 54 observations per layout/method. Arithmetic means of phases from the same intervals add to the mean total. Across path-major methods, generation occupied 91.5–92.6% of mean total and the allocation/bridge/calculation/aggregation phase 7.4–8.5%; step-major added layout conversion of 18.7–19.3% of mean total. These are characteristics of this NumPy/C++ pipeline and the declared equal-weight matrix. They do not specify a production workload mix or the cost of an all-C++ generator. Separately timed prepared durations are never spliced into whole-interval decompositions.

Supported bounded observation: nearly full logical lane occupancy did not imply a uniform runtime improvement in the tested implementation. Layout, path lifetime and the chosen timing scope must remain explicit when reporting results. Bookkeeping and per-lane input access are included by the code; their individual hardware costs were not isolated. Increased load, unavailable process/thermal inspection and broad variation remain limits on quantitative conclusions.

`analysis/main_views.py` produces the descriptive tables and annotated PNG/SVG figures without running pricing. Four analysis counterexample tests check additive means versus phase medians, matched-summary semantics, unique-seed workload counting and final-date knock-out classification; all passed alongside the seven runner tests. Required root debug configure/build/CTest also passed. A separate export audit recomputed all CSV values and summaries from the raw observations, verified source/artifact hashes, checked plot ranges and confirmed the main manifest and observations were unchanged.

The figure sequence is a small retained-path illustration, a separately labelled mechanism schematic, a six-case fixed/refill comparison with raw timings and scalar medians, and a complete-cost composition. The chronological diagnostic remains supporting evidence. No new benchmark observations were collected for analysis. The bounded investigation is complete with the stated limitations; next is figure/claim review and article integration, without automatically extending the campaign.

## Float/double extension preparation, 14 November

At the author's request, separate FP32 scalar/fixed/refill implementations and a
precision worker are prepared. FP64 calls the original `barrier_core`; FP32 uses
float factors, updates, comparisons, discount and payoff arithmetic. Both use
ordered FP64 aggregation. Separate build directories and libraries preserve the
original measured source files, executables and observations.

Root debug configure/build/CTest passed (two tests). Precision debug, ASan/UBSan
and release configure/build/CTest passed (four tests each, including the original
pricing suite). All twenty Python runner/analysis tests passed, including nine
new precision counterexample/identity checks. The complete untimed independent
verification passed 108 precision/method/layout/seed/barrier configurations,
checking every ordered payoff, lifetime and knock-out flag against the relevant
date-wise FP32 or FP64 oracle. A separate untimed 257-path/17-date smoke passed all
twelve candidates. Literal/Decimal fixtures and a constructed barrier-rounding
counterexample also passed.

The release worker reports four float lanes and two double lanes. Its generated
FP32 assembly contains `fmul ... .4s`. This establishes the compiled vector
arithmetic, not a performance improvement. Original double C++ files, retained
release binaries and original main-campaign manifest/observations retain their
preparation-start hashes.

The untimed 8192-path verification found one cross-precision knock-out
disagreement in seed 47 at barrier 105. A changed knock-out flag need not change
the terminal payoff: surviving paths can also pay zero. Per-seed/barrier payoff
errors, signed price differences, and an FP64 reference using rounded FP32 input
factors are retained. This is a numerical observation on the checked synthetic
inputs, not a general accuracy bound or an accepted financial error threshold.
The verification analysis produced accuracy tables/figures and correctly
produced no runtime ratios or runtime plot.

The prepared timing pilot has 648 sequential prepared-input observations at
8192 paths and 252 dates, with six precision/method order rotations per case. It
has not run. Preflight checks stable AC, load, optimized artifacts and freshness;
the execution path checks hashes, resources, power and independent outputs.
Next: run the precision pilot once in a quiet AC-powered window, retain all
observations, then use `analysis/analyze_precision.py` before deciding whether a
larger campaign is justified. No original timing campaign was rerun.

## Repository relocation, 15 November

Pricing C++ files and original evidence retain their bytes. Active build paths,
runner snapshots and plotting-style paths now use `studies/barrier-options/` and
`publication/visual-style.json`. The measured checkout remains available in its
immutable source archives. Relocation itself collected no pricing observations.
The current build/check record is retained separately in `local/migration/`.
