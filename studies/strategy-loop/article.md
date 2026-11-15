# One market, a thousand strategies: which way should the loop run?

*A C++ experiment about replaying trading rules, arranging data, and the work behind a parameter search.*

> Working draft, 15 November 2026. The C++23 layout example is compiled and checked; the backtest engine and performance measurements are still pending. Figure previews contain fictional values. Bracketed result and dataset passages remain open.

## One rule, quite a few settings

Suppose you have a trading rule simple enough to explain over coffee: hold a stock while its recent trend looks stronger than its longer-term trend, and sit out when that changes. Before getting too attached to it, you would probably want to try a few settings. How recent is recent? How long should the longer trend be?

Those two choices give us a grid to explore. With 48 possible settings for our smoothed price, there are 1,128 ways to choose a shorter and a longer one. Each pair gives us a version of the same rule, all looking at the same market history. The computer is perfectly happy to keep trying; deciding what to make of the results is our problem.

This is where my interest in trading meets the sort of question I can investigate in C++. The straightforward implementation is to pick a pair, replay the history, save the result, and move on to the next pair. But we could also read the first market event, update every version of the strategy, and then move to the next event. Each strategy would still see its own history in order. We would be taking a different route through the same work.

I want to find out what that route costs once each strategy has an account to update and some results to produce. There is also a second choice underneath the loops: how the values they read are arranged in memory. C++23's `mdspan` gives us a way to make that choice explicit without changing the coordinates we use to access them.

**[FIGURE 1 — A thousand versions of one rule]**

[Place the triangular fast/slow parameter heatmap here once it is backed by checked results and an identified dataset. Each tile is one configuration's net return over the same period. The current preview is fictional and cannot fill this slot as a result.]

## Give each strategy its own little account

An exponential moving average, or EMA, smooths a price by combining the latest observation with its previous smoothed value. We will use:

```text
EMA[t] = alpha * close[t] + (1 - alpha) * EMA[t - 1]
alpha  = 2 / (span + 1)
```

A shorter span gives the latest price more weight, so its average reacts more quickly. Our rule holds the asset when the fast average is above the slow one, and holds cash otherwise. A 10-bar/30-bar pair and a 12-bar/40-bar pair are two configurations. A bar is one time interval with an opening and closing price; the interval for the eventual market example is still to be selected.

Each configuration gets its own simulated account. They share the price history and indicator values, but each has its own cash, holding and record of what happened. This independence is what will let us rearrange their updates. If two strategies competed for the same cash or the same available fill, changing their order could change the answer.

There is one timing detail to get right before worrying about the computer's clock. A signal calculated from Monday's closing price can affect the trade at Tuesday's open in our model. It cannot buy at Monday's open using information from later that day. So each update first carries out the previous completed bar's instruction, values the account at the current close, and prepares the next instruction.

For example, suppose an account has 1,000 in cash and its previous signal says to buy. At an opening price of 100, it buys 10 shares if we temporarily ignore fees. If the close is 102, the account is worth 1,020. A sell signal calculated from that close will wait until the following open. If it opens at 99, those shares sell for 990. The overnight move belongs in the result; rearranging our loops must preserve it too.

The checked engine will use a small explicit proportional fee, fractional holdings, and a final liquidation rule. The fee-free numbers above are just a hand-worked illustration. The [experiment brief](brief.md) fixes the accounting details so that all four implementations do the same job.

[DATASET — Select and document one instrument, provider, period, bar interval and price convention before producing a market-return heatmap. Deterministic synthetic input comes first for correctness; it will be labelled synthetic wherever used.]

## Two ways to walk through the work

Imagine a spreadsheet with market events down the rows and strategy configurations across the columns. We can finish one column before starting the next, or finish one row before moving down. Either way, every individual strategy travels from the top of its column to the bottom.

The strategy-first route keeps one account in hand while it works through the history. The event-first route keeps returning to a collection of accounts while advancing through the market events. That gives us a plausible tradeoff to examine: access to the market features on one side, and access to strategy state on the other. We have not yet measured which matters more.

**[FIGURE 2 — Two routes, then two storage layouts]**

[Keep the traversal schematic: blue down the strategy columns, red across the event rows. Below it, explain the separate feature table and its two storage orders. Logical traversal arrows are not elapsed-time traces.]

The two loop nests look like this. `step` will contain the same accounting in both; this is still engine pseudocode:

```cpp
for (std::size_t s = 0; s < configs.size(); ++s) {
    for (std::size_t t = first_bar; t < bars.size(); ++t) {
        step(states[s], configs[s], bars[t],
             features[t, configs[s].fast], features[t, configs[s].slow]);
    }
}

for (std::size_t t = first_bar; t < bars.size(); ++t) {
    for (std::size_t s = 0; s < configs.size(); ++s) {
        step(states[s], configs[s], bars[t],
             features[t, configs[s].fast], features[t, configs[s].slow]);
    }
}
```

Before either loop starts, we will calculate each distinct EMA once. Many pairs reuse the same average, so recalculating it for every strategy would make the comparison unnecessarily expensive. Both traversal orders get the same shared feature values and produce a result for every configuration, in the same configuration order.

## The other table, and where `mdspan` fits

The feature table is different from the spreadsheet of strategy updates. Its rows are bars, but its columns are EMA windows. A thousand configurations can share a few dozen indicator columns.

Take three bars and just two indicator columns, A and B:

```text
             A    B
bar 0       A0   B0
bar 1       A1   B1
bar 2       A2   B2

History together:   A0 A1 A2 B0 B1 B2
Snapshot together:  A0 B0 A1 B1 A2 B2
```

In the first arrangement, following one indicator through time takes us through neighboring values. In the second, neighboring values describe different indicators at the same event. Both represent the same logical table.

Here is the C++ view we can use for either:

```cpp
template<class Layout>
using FeatureView = std::mdspan<const double,
                              std::dextents<std::size_t, 2>, Layout>;
```

The backing buffer owns the numbers; `mdspan` holds the information needed to find them. With logical dimensions `[bar, window]`, `layout_left` puts successive bars next to each other. `layout_right` puts successive windows next to each other. In both cases, the expression is `features[t, w]`. These mappings follow the [standard layout definitions](https://eel.is/c%2B%2Bdraft/mdspan.layout.left.overview) and [their right-layout counterpart](https://eel.is/c%2B%2Bdraft/mdspan.layout.right.overview).

For N bars and W windows, the underlying offsets are `t + N * w` and `t * W + w`. The policy makes those mappings explicit. It does not turn one backing array into the other. If we change the view without arranging the data to match, we read different values. The owner must also remain alive, without an invalidating reallocation, for as long as we use its view.

The [small runnable example](examples/layout.cpp) checks this with six invented values, both sets of strides and a deliberately mismatched view. It builds on my existing GCC 16.2 setup in C++23 mode and passes sanitizer checks. [GCC's release notes](https://gcc.gnu.org/gcc-16/changes.html) list `mdspan` support; the local check establishes that the particular form used here works. It says nothing yet about backtest speed or the cost of the abstraction.

That leaves four combinations:

| Traversal | Feature storage |
| --- | --- |
| Finish one strategy's history at a time | One indicator's history together |
| Finish one strategy's history at a time | One event's indicator snapshot together |
| Update every strategy for one event at a time | One indicator's history together |
| Update every strategy for one event at a time | One event's indicator snapshot together |

The state representation, strategy ordering and arithmetic stay fixed. This lets us ask about traversal and layout separately. `mdspan` is how we express the layout choice here; there is no raw-pointer-versus-view comparison, and no assumed SIMD benefit.

## What we will measure

First we need to check the decisions, holdings, trade counts and numerical summaries against an independent reference. Matching the final return alone would leave too much room for two different histories to happen to end at the same number. Small fixtures will include an overnight gap, equality between indicators, no trades, and a position still open at the end.

Then we can time a complete replay and divide by the number of configurations times the number of eligible bars. That gives us nanoseconds per strategy-bar: the cost of updating one configuration for one event, averaged over the replay. It is a throughput measure derived from the full interval, not the latency of an individual market event.

**[FIGURE 3 — What does one strategy-bar cost?]**

[Two panels, one per physical feature layout. Configuration count K on the horizontal axis; replay nanoseconds per strategy-bar vertically. Blue strategy-first, red event-first. Hold history length N and feature population W fixed within a comparison. Retain matched process observations and define the descriptive center. No assumed crossover or smoothed confidence band.]

[RESULTS — Report the observed ordering and variation, including an unresolved difference if that is what we find. Inspect the measured build's compiler diagnostics before discussing vectorization. Timings alone will not identify cache misses or bandwidth limits.]

I also want the complete-run cost: preparing the features in the required storage order, setting up the accounts, replaying the history, and producing the summaries. A layout that helps the replay may take work to prepare. Whether it is useful depends partly on how often that preparation can be reused.

**[OPTIONAL FIGURE 4 — What did the whole run cost?]**

[Include the four stage breakdowns only if preparation changes the practical interpretation. Derive stages from the same complete intervals; otherwise report whole-run totals in a small table. Record memory and any conversion scratch separately.]

## What this could change in a research tool

The useful outcome would be a reason to organize an independent parameter sweep one way under a stated workload. That could help when trying settings for a signal or replaying scenarios in a research application. A shared portfolio or an execution simulator with competition for fills would need its dependencies examined before applying the same loop transformation.

Making these runs faster also makes it easier to try more settings until something looks convincing. Our parameter heatmap will describe one chosen history. It will not establish that its brightest tile is a good strategy for the next one. Bailey and colleagues discuss this selection problem in [*The Probability of Backtest Overfitting*, February 2015](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf).

[CONCLUSION — Follow the measured outcome: a workload/layout-dependent advantage, little material difference, or a replay gain absorbed by preparation. Explain the supported implementation choice and its conditions. No winner is written in advance.]

## Reproduction details to complete

[Engine/data revision; provider, period and price convention; accounting contract; host/compiler/flags; N/K/W and common warm-up; bytes and timing boundaries; independent correctness outcomes; retained individual observations; exact reproduction commands. Only the layout example has run so far.]
