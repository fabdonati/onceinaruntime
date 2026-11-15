# One market, a thousand strategies: which way should the loop run?

How do loop order and physical feature layout affect a parameter sweep of
independent trading strategies, while preserving every decision and result?

## Current status

Proposal and preliminary manuscript only. No strategy implementation, market-data
processing, exact `mdspan` compile probe or performance measurements exist.
Preview charts use explicitly fictional values for design review.

Next: review the premise, freeze the accounting/data contract and a bounded
matrix, check the C++23 setup and implement an independent correctness reference.
Do not interpret preview shapes as expected results.

| Material | Location |
| --- | --- |
| Preliminary article | [article.md](article.md) |
| Proposed experiment and unresolved choices | [brief.md](brief.md) |
| Figure roles and metrics | [figure-plan.md](figure-plan.md) |
| Fictional storyboard | [previews/figures/storyboard.png](previews/figures/storyboard.png) |
| Preview generator | [previews/draw_previews.py](previews/draw_previews.py) |

Regenerate design previews into a new directory, without running an experiment:

```sh
MPLCONFIGDIR=build/matplotlib XDG_CACHE_HOME=build/cache .venv/bin/python \
  studies/strategy-loop/previews/draw_previews.py --output build/strategy-previews
```

C++ source, test and build folders will be added when implementation starts.
