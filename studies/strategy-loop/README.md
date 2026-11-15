# One market, a thousand strategies: which way should the loop run?

How do loop order and physical feature layout affect a parameter sweep of
independent trading strategies, while preserving every decision and result?

## Current status

The manuscript now explains the financial example, both traversal orders and
the separate feature layouts. Working accounting defaults are in the brief.
The actual C++23 `mdspan` layout example passes on GCC 16.2, including sanitizers.

No backtest engine, historical dataset or performance measurements exist yet.
Preview charts remain fictional. See [findings](findings.md) for executed checks.

Next: implement the independent accounting reference and deterministic fixtures,
then the four equal-output replay variants. Historical data and a bounded timing
matrix follow the correctness gate. No winner is assumed.

| Material | Location |
| --- | --- |
| Preliminary article | [article.md](article.md) |
| Proposed experiment and unresolved choices | [brief.md](brief.md) |
| Runnable C++23 layout example | [examples/layout.cpp](examples/layout.cpp) |
| Executed checks and limits | [findings.md](findings.md) |
| Figure roles and metrics | [figure-plan.md](figure-plan.md) |
| Fictional storyboard | [previews/figures/storyboard.png](previews/figures/storyboard.png) |
| Preview generator | [previews/draw_previews.py](previews/draw_previews.py) |

Regenerate design previews into a new directory, without running an experiment:

```sh
MPLCONFIGDIR=build/matplotlib XDG_CACHE_HOME=build/cache .venv/bin/python \
  studies/strategy-loop/previews/draw_previews.py --output build/strategy-previews
```

The small layout example is included in the root correctness builds:

```sh
cmake --preset debug
cmake --build --preset debug
ctest --preset debug
```

It is not a trading engine or benchmark. Set `OIR_STRATEGY_EXAMPLES=OFF` when
configuring a toolchain without C++23 `mdspan`; the barrier study remains C++20.
