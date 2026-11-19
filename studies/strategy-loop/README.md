# One market, a thousand strategies: which way should the loop run?

How do loop order and physical feature layout affect a parameter sweep of
independent trading strategies, while preserving every decision and result?

## Current status

The draft was revised on **19 November 2026** to make the layout-dependent
performance claim explicit in the opening, results and conclusion. Its six
figures now include approved profile cards, the crossover timing chart and
the account-file illustration in a separate mechanism section, before the
preparation-cost discussion. Next: read the complete
article for flow and clarity; no new measurements were required for this edit.

The [mechanism inspection](mechanism-check.md) reached its static stopping
point on **17 November 2026**. Compiled steady paths show register-held account
state for strategy-first, versus 32 B of account reads and 16 B of writes per
unchanged update for event-first. Feature addressing and branch paths also
differ. These are inspected operations, not cache/cycle measurements. Counter
profiling is unavailable through the checked toolchain, so runtime attribution
remains open. Debug checks passed; the draft includes a new
[mechanism illustration](figures/09-account-state-mechanism.png), now using an
account-file metaphor to show register retention and repeated account access.

The bounded [mdspan/manual-indexing check](mdspan-check.md) also completed on
**17 November 2026**. Both complete replay functions have 645 static instructions;
all address calculations and memory accesses match. Eleven encodings differ
only in operand order and corresponding comparison conditions. Manual indexing
saves no instructions here. Debug and sanitizer checks, eight full-size output
gates and 32 pilot observations passed. Pilot background load rose, so no precise
timing-overhead percentage is claimed. The draft includes the scoped finding.

The historical extension completed on **17 November 2026** using the supplied
QQQ export from Alpaca SIP. The audit accepted **291,840 regular-session minute
bars across 752 sessions**, with no missing expected minutes or projection
mismatches. Original exports remain unchanged under ignored `local/data/alpaca/`.

All debug checks passed, including real-data trace excerpts and an overnight
boundary. The independent full-scale gate passed **48 untimed workers**; the
separate pilot passed **48 observations** and main campaign **384 observations**.
No C++ implementation changed. Main measurement ran on AC power after a full
minute of low recorded load; measurement load stayed between **1.977 and 2.140**.
Every output and final integrity check passed. All 1,346 archived pilot/main
files were hash-verified.

The storage-dependent ordering repeated in all twelve historical N/K/profile
cells: strategy-first within history storage, event-first within snapshot
storage, and strategy-first/history lowest overall. The three full-grid activity
rates are similar, so the result extends input coverage without establishing
behaviour across radically different computational regimes.

The [draft](article.md) uses the historical contour, profile cards, timing
crossover, account-state illustration and complete-cost view. The
[figure index](figures/README.md) links these to their evidence. Earlier synthetic
campaigns remain separate in [results](results/README.md).
Raw histories, references, process monitoring, exact commands and source/build
snapshots remain in `local/evidence/strategy-loop/historical-20261117/`.

Next: author review of the article's explanation and chart readability. The
bounded historical implementation, verification and measurement plan is complete;
no additional timing run is required for these figures. See [findings](findings.md),
the [historical protocol](historical-plan.md) and [run guide](benchmark.md).

Further extensions are scoped in [follow-up options](follow-up-options.md):
counter-based mechanism attribution, streaming response latency and financial
robustness. The abstraction and static mechanism checks above are complete;
the original traversal/layout plots and measurement archives are unchanged.

| Material | Location |
| --- | --- |
| Preliminary article | [article.md](article.md) |
| Proposed experiment and unresolved choices | [brief.md](brief.md) |
| Historical workload protocol and status | [historical-plan.md](historical-plan.md) |
| Alpaca QQQ data acquisition tool | [tools/alpaca/README.md](tools/alpaca/README.md) |
| Runnable C++23 layout example | [examples/layout.cpp](examples/layout.cpp) |
| Five-bar account and arithmetic | [examples/account.md](examples/account.md) |
| Shared accounting and four replay routes | [src/replay.cpp](src/replay.cpp) |
| Independent transaction-ledger reference | [analysis/reference.py](analysis/reference.py) |
| Correctness, pilot and plot commands | [benchmark.md](benchmark.md) |
| Checked historical account illustration | [figures/08-historical-accounts.png](figures/08-historical-accounts.png) |
| Main/pilot timings and complete-cost figures | [results/README.md](results/README.md) |
| Executed checks and limits | [findings.md](findings.md) |
| mdspan/manual-indexing comparison | [mdspan-check.md](mdspan-check.md) |
| Compiled paths and mechanism limits | [mechanism-check.md](mechanism-check.md) |
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
