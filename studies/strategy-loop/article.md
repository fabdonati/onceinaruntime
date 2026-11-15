# One market, a thousand strategies: which way should the loop run?

*A C++ backtesting experiment about loop order, memory layout, and the work hidden behind a parameter search.*

> Preliminary skeleton, 15 November 2026. Opening and transitions are proposed prose. Bracketed passages are writing/evidence placeholders. No implementation or performance measurements exist for this question. Figure previews use fictional values solely to review their design.

## 1. How one trading rule becomes a thousand backtests

Suppose you have a trading rule simple enough to explain over coffee: follow the price while its recent trend looks stronger than its longer-term trend, and sit out when that changes. Before getting too attached to it, you would probably want to try a few settings. How recent is recent? How long should the longer trend be?

Those two choices give us a grid to explore. A few dozen possibilities on each axis are enough to turn one idea into roughly a thousand versions of it, all looking at the same market history. The computer is perfectly happy to keep trying; deciding what to make of the results is our problem.

That setup connects two things I want to explore here: how trading software works, and what happens when a fairly ordinary C++ design meets a larger workload. The first implementation almost writes itself. Pick a setting, replay the history, save the result, and move on to the next setting. But we could also read the first market event, update every strategy, and then move on to the next event. Each strategy still sees its own history in order. The route through the work changes.

**[FIGURE 1 — What are we asking the computer to do?]**

[One triangular parameter heatmap: fast moving-average span horizontally, slow span vertically, net return in the chosen historical period encoded by color. Show only valid fast < slow combinations. This establishes the workload; all implementations must reproduce the same result for each tile. Do not duplicate the heatmap for each implementation.]

*Proposed caption:* Each valid tile is one version of the same rule. The color describes its result on this particular history. The implementation comparison below must preserve every tile's trading decisions and results.

## 2. Give the financial example just enough machinery

An exponential moving average is a way to smooth a price while giving more weight to recent observations. We will compare a faster average with a slower one: take a long position when the fast average is above the slow average, and otherwise hold cash. Here, long just means that the position benefits when the price rises.

[Explain the recurrence with one short equation and a small price/average illustration only if needed: EMA(t) = alpha * close(t) + (1 - alpha) * EMA(t-1). Define alpha = 2 / (span + 1). Freeze initialization, warm-up and equality behavior in the experiment brief.]

[Specify the accounting contract before implementation: a signal calculated from a completed bar becomes eligible at the following bar's open; identical position sizing, transaction-cost model, mark-to-market rules and final-position treatment in every route. Use a deliberately simple long/cash model. Exact accounting remains a prerequisite, not a result.]

There is already an easy way to waste work here. Many parameter pairs reuse the same moving average, so computing it again for every pair would make the baseline unnecessarily expensive. We will calculate each distinct average once and let both replay orders use those same values. That leaves a more focused question: how should the replay visit the features and strategy states?

[Describe one liquid instrument and one frozen, documented dataset after selection. The performance question can first use deterministic synthetic input for verification. Historical data is needed before presenting the heatmap as a market example. No data source or period has been selected.]

## 3. Walk down the history, or across the strategies

Imagine a spreadsheet with market events down the rows and strategy settings across the columns. One approach finishes a column before starting the next; the other finishes a row. In both cases, each individual strategy moves from the top of its column to the bottom. We can change the visit order because these simulated strategies have independent states and do not compete for capital or fills.

**[FIGURE 2 — Two traversals, then two memory layouts]**

[A blue path travels down one strategy column at a time. A red path travels across one event row at a time. Beneath them, show two small memory strips: a complete indicator history stored together, and all indicator values for one event stored together. These are distinct choices; crossing them gives four variants. This is a logical traversal diagram, not a timeline.]

The two loop nests would look roughly like this. Both call the same state-transition function:

```cpp
// Illustrative pseudocode; step() and its accounting are not implemented.
// features(t, window) denotes a read-only, two-dimensional view.
for (std::size_t s = 0; s < configs.size(); ++s) {
    auto& state = states[s];
    const auto config = configs[s];
    for (std::size_t t = first_bar; t < last_bar; ++t) {
        step(state, config, bars[t], features(t, config.fast),
             features(t, config.slow));
    }
}

for (std::size_t t = first_bar; t < last_bar; ++t) {
    const auto& bar = bars[t];
    for (std::size_t s = 0; s < configs.size(); ++s) {
        const auto config = configs[s];
        step(states[s], config, bar, features(t, config.fast),
             features(t, config.slow));
    }
}
```

[Follow the price/features/state accesses for a single update. The strategy-first route repeatedly revisits history while concentrating on one strategy state. The event-first route revisits a set of states while progressing through history once in logical event order. Describe access patterns; do not equate source-level accesses with physical memory reads.]

## 4. The C++ part: make the layout an explicit choice

There is a second decision hiding under `features(t, window)`: which neighboring values are actually next to each other in memory? We can keep the logical coordinates the same while arranging the backing storage in either order. This is a useful place for C++23's `std::mdspan`, a non-owning multidimensional view with a layout policy. It lets us express the mapping separately from the owning buffer. Changing a view's policy does not transpose an existing dataset; the backing values must be arranged to match it. [C++ working draft: multidimensional views](https://eel.is/c%2B%2Bdraft/views.multidim)

[Introduce the proposed view, after a local compile check. For logical dimensions [bar, window], layout_left gives bar stride 1; layout_right gives window stride 1. Backing buffers are separately materialized from the same canonical feature values.]

```cpp
// Proposed C++23 type; toolchain support and generated code still need checking.
template<class Layout>
using EmaView = std::mdspan<const double,
                          std::dextents<std::size_t, 2>, Layout>;
```

[One concise 2 x 2 table: strategy-first/event-first crossed with history-contiguous/snapshot-contiguous features. Hold strategy-state representation, arithmetic, config ordering and output requirements constant. Do not also introduce AoS/SoA, explicit SIMD, multithreading or float/double into this first comparison.]

[Explain why independent strategy updates are a possible vectorization dimension, while a strategy's own state links one time step to the next. Inspect compiler reports and generated code before saying that a loop vectorized. GCC exposes optimization reports for this purpose. No SIMD speedup is assumed. [GCC optimization reports](https://gcc.gnu.org/onlinedocs/gcc/Developer-Options.html)]

## 5. Which version wins, and under which workload?

[First report independent correctness checks: decisions, positions, trade counts and numerical results. Do not proceed to performance interpretation if the four variants disagree on the required output.]

**[FIGURE 3 — The cost of one strategy-bar]**

[Two small-multiple line charts, one per feature layout. Horizontal axis: number of parameter pairs K. Vertical axis: replay nanoseconds per strategy-bar, lower is better. Blue: strategy-first. Red: event-first. Fix history length and feature set within this comparison; show matched process observations, not an unsupported confidence band. Repeat for a second history length only if it changes the engineering decision.]

*Proposed caption:* Each point summarizes repeated complete replays of the same workload. One strategy-bar means updating one strategy with one eligible bar. Layout is held fixed within each panel. [Insert exact workload, host/compiler/revision, observation structure and summary definition after measurement.]

[Results paragraph: state the observed ordering, its magnitude and its conditions. If results overlap or the ordering changes, preserve that outcome. Do not prewrite a crossover or universal winner.]

[Mechanism paragraph: connect compiler evidence, state/feature sizes and access patterns to plausible explanations. Timing alone cannot identify a cache boundary, memory bandwidth limit or vectorization cause.]

**[OPTIONAL FIGURE 4 — What did the whole run cost?]**

[Four horizontal stacked bars at one decision-relevant workload: feature preparation/materialization, state setup, replay and summary output. Each bar is one complete variant. Include this figure only if preprocessing meaningfully changes the reader's choice; otherwise give the totals in a short table. A fast kernel can be a small part of a complete run.]

[Give whole-run elapsed time in the text even if the optional figure is omitted. Separately record memory footprint; report the common footprint once rather than inventing a memory contest between equal-size buffers.]

## 6. What this changes in a research tool

[Close with the supported design decision: when an independently stateful parameter sweep benefits from a particular traversal/layout combination, what preparation it requires, and when the simpler route remains adequate. Connect to signal sweeps, parameter studies and scenario replays with genuinely independent states.]

There is another consequence to keep in mind: making it easier to test more settings also makes it easier to find something that looks impressive by chance. The parameter map describes this chosen history. A useful statistical investigation would need a separate selection and validation protocol; the fastest replay does not establish that its best-looking strategy will make money. [Bailey et al., *The Probability of Backtest Overfitting*, February 2015](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf)

[Final takeaway remains open until evidence exists. Possible outcome forms: a layout-dependent advantage; little material difference for the intended workload; a kernel benefit largely absorbed by preparation. Follow with a verified public code/reproduction link when one exists.]

## Proposed technical footer

[Dataset/provider/date interval/licensing; strategy and accounting definitions; C++ standard/compiler/flags; machine; N/K/W and warm-up; feature/state/output bytes; complete timing boundary; raw process observations; exact code revision and dirty state; passed correctness checks; reproduction commands. No public experiment URL exists yet.]
