# Strategy-loop figures

## Current article figures

| Figure | Evidence |
| --- | --- |
| [Account contours](08-historical-accounts.png) | [Checked summaries for all 1,128 accounts](historical-accounts.csv) in the selected directional QQQ window |
| [Traversal schematic](../previews/figures/02-traversal-and-layout.png) | Logical update order and feature layout example |
| [Historical profile cards](05-historical-profiles.png) | Normalized prices and position activity for three selected QQQ windows |
| [Timing crossover](06-historical-ratios.png) | Individual timings for the directional full-grid example and paired ratios for all 12 workloads |
| [Account-state illustration](09-account-state-mechanism.png) | [Inspected compiler paths](../results/mechanism-paths.json) for unchanged-position updates |
| [Complete computation cost](07-historical-whole.png) | Stage times and individual totals for the directional 64-strategy example |

The [historical results](../results/README.md#historical-qqq-campaign-17-november-2026)
retain all 384 timing observations. The [benchmark guide](../benchmark.md) explains
how to regenerate the figures from an audited campaign. Raw market prices and
campaign archives stay local.

## Synthetic account illustration

`01-synthetic-accounts.png` and `.svg` show actual computed account summaries
from the untimed correctness gate: 32,768 generated bars, seed 11, spans 2..96
by 2, all 1,128 fast<slow pairs, initial capital 1,000 and one-basis-point fees
on each side. All accounts share the first 96 bars as warm-up. These are
invented prices with alternating drift, not a market dataset.

[`accounts.csv`](accounts.csv) is byte-identical to the checked C++ summary;
the other three implementations produced identical bytes and the independent
Python ledger matched under the declared tolerance. Invalid fast>=slow pairs
are blank in the chart. The color scale is net period return in percent and is
centered at zero. The figure was visually inspected after rendering.

[`provenance.json`](provenance.json) retains input-manifest, summary, plotting
source and style hashes with versions and workload parameters. It is a curated
copy that omits local command paths; its original-record hash links to the
unchanged full metadata retained with private evidence. Original verification
records have not been rewritten.

Reproduce from a completed untimed run using a new output directory:

```sh
MPLCONFIGDIR=build/matplotlib XDG_CACHE_HOME=build/cache .venv/bin/python \
  studies/01-strategy-loop/analysis/plot.py --example \
  --input build/strategy-verify --output build/strategy-account-figure
```

This figure explains what a parameter sweep computes. It is not a runtime
measurement or evidence of a profitable trading rule. The traversal diagram
remains in `../previews/figures/02-traversal-and-layout.png`; it is explicitly a
schematic. Other return/timing previews in that folder contain fictional values.

## Earlier synthetic timing figures

`03-replay-cost-main` and `04-whole-run-main` (PNG/SVG) use the completed main
campaign's 576 observations. Both were
visually reviewed, including legend/caption separation and plot limits.

The corresponding `-pilot` files retain the earlier exploratory 192-observation
views, explicitly labelled PILOT. They are not the article's measured figures.
Numeric tables, exact selection rules, original-metadata hashes and the material
host-load limitation are in [results](../results/README.md). No sample was removed
to draw either version. Each complete-cost stack is one actual run, not a sum of
stage medians.
