# 02 · When an option disappears, what happens to its SIMD lane?

A C++20 study of what to do when one simulated price path ends before the
others in its SIMD group. The three implementations process one path at a
time with early exit, use fixed SIMD groups, or load a new path into a lane
as soon as it finishes.

Start with the [article draft](article.md). The [toolchain and run guide](environment.md)
shows how to build the pricer, check every path and reproduce the measurements.

The double-precision run recorded 324 observations with prepared input and 324
for the full pricing pipeline. Refill kept almost every logical lane busy.
Its time advantage depended on the barrier and the input layout, and background
load rose during the test. The [findings](findings.md) give the medians, ranges
and conditions for each case.

The [float versus double extension](precision/README.md) has passed its
correctness checks. The timing pilot remains open. Changing precision changes
both the number of lanes and the size and arithmetic of each value.

| To find | Open |
| --- | --- |
| Payoff rules and comparison setup | [brief.md](brief.md) |
| Every timing, paired comparisons and phase means | [results](results/README.md) |
| Charts and the two-lane example | [figure index](figures/README.md) |
| C++ pricer and test fixtures | [src](src), [tests](tests) |
| Python reference, runner and plots | [analysis](analysis) |
| Sources | [references.md](references.md) |
