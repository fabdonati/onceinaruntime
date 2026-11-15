# One market, a thousand strategies: which way should the loop run?

How do loop order and physical feature layout affect a parameter sweep of
independent trading strategies, while preserving every decision and result?

## Current status

The four C++23 replay variants are implemented and checked against an independent
Python transaction ledger. Debug, sanitizer and release correctness builds pass.
The larger untimed matrix also passes: both history lengths, both seeds, all
three configuration counts and all four variants.

The article includes a checked synthetic account heatmap, the traversal diagram
and two charts from the completed **576-observation main campaign**, following a
192-observation pilot. The five-bar account is runnable. Strategy-first has lower
median cost within history storage, event-first within snapshot storage;
strategy-first/history is lowest across all four candidates in all 18 main
workload/seed cells. Host load rose during timing, so claims remain scoped to
these observed runs and inputs.

Next: read the complete draft and charts together, review its voice and bounded
claim, and decide whether a better-isolated reproduction is needed before release.
The implementation, independent correctness, pilot and main stopping points are
met. No publishing or push has occurred. See [findings](findings.md),
[results](results/README.md), the [measurement plan](measurement-plan.md) and
the [run guide](benchmark.md).

| Material | Location |
| --- | --- |
| Preliminary article | [article.md](article.md) |
| Proposed experiment and unresolved choices | [brief.md](brief.md) |
| Runnable C++23 layout example | [examples/layout.cpp](examples/layout.cpp) |
| Five-bar account and arithmetic | [examples/account.md](examples/account.md) |
| Shared accounting and four replay routes | [src/replay.cpp](src/replay.cpp) |
| Independent transaction-ledger reference | [analysis/reference.py](analysis/reference.py) |
| Correctness, pilot and plot commands | [benchmark.md](benchmark.md) |
| Checked synthetic account illustration | [figures/01-synthetic-accounts.png](figures/01-synthetic-accounts.png) |
| Main/pilot timings and complete-cost figures | [results/README.md](results/README.md) |
| Executed checks and limits | [findings.md](findings.md) |
| Figure roles and metrics | [figure-plan.md](figure-plan.md) |
| Fictional storyboard | [previews/figures/storyboard.png](previews/figures/storyboard.png) |
| Preview generator | [previews/draw_previews.py](previews/draw_previews.py) |

Regenerate design previews into a new directory, without running an experiment:

```sh
MPLCONFIGDIR=build/matplotlib XDG_CACHE_HOME=build/cache .venv/bin/python \
  studies/strategy-loop/previews/draw_previews.py --output build/strategy-previews
```

The engine, independent accounting checks and layout example are included in
the root correctness builds:

```sh
cmake --preset debug
cmake --build --preset debug
ctest --preset debug
```

Set `OIR_STRATEGY_EXAMPLES=OFF` to omit this entire study when configuring a
toolchain without C++23 `mdspan`; the barrier study remains C++20.
