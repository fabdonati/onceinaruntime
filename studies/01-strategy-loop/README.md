# 01 · One market, a thousand strategies

A C++23 study of two ways to replay the same EMA strategies. The loop can
finish one account's history at a time or update every account at each bar.
The input can also store each indicator's history together or each bar's
snapshot together. All four combinations produce the same ordered account
summaries.

Start with the [article draft](article.md). To try the five-bar example or run
the longer tests, follow the [reproduction guide](benchmark.md).

## Results

With history storage, finishing one account at a time gave the lowest median
replay time. With snapshot storage, updating every account at each bar was
faster. Strategy-first with history storage had the lowest median across all
four combinations in each of the twelve historical workloads. The main QQQ
campaign retained 384 observations on an Apple M3 with GCC 16.2.

The compiled strategy-first loop keeps account state in registers across bars.
On the inspected event-first paths, a steady update reads 32 bytes and writes
16 bytes of account fields. These are instruction operands. Attributing the
timings to cache behavior or other CPU costs would need profiling.

The [separate `mdspan` check](mdspan-check.md) found the same address and memory
operations with manual indexing. Background load rose during that timing pilot,
which limits comparisons of the small timing differences.

The historical study and figures are complete. Next is the editorial pass for
Substack. The earlier synthetic campaigns are available in the results.

## Files

| To find | Open |
| --- | --- |
| Five-bar accounting example and C++23 layout example | [account.md](examples/account.md), [layout.cpp](examples/layout.cpp) |
| Account rules and independent ledger | [brief.md](brief.md), [reference.py](analysis/reference.py) |
| QQQ inputs and workload selection | [download guide](tools/alpaca/README.md), [historical plan](historical-plan.md) |
| Every timing and the measurement limits | [results](results/README.md), [findings](findings.md) |
| Figures and their inputs | [figure index](figures/README.md) |
| Reviewed instructions and operand counts | [mechanism report](mechanism-check.md) |
| C++ replay and test fixtures | [src](src), [tests](tests) |
