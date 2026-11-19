# Article and figure plan

Updated 19 November 2026. The draft now uses the completed historical QQQ
campaign: 48 untimed checks, 48 pilot and 384 main observations. The old synthetic
figures remain supporting artifacts; fictional previews are not measured results.

The current figures have distinct jobs:

| Position | Asset | Purpose |
| --- | --- | --- |
| Opening | `figures/08-historical-accounts.png` | Show the 1,128 required account outcomes, using the preselected directional window and actual signed returns |
| Loop explanation | `previews/figures/02-traversal-and-layout.png` | Explain logical traversal versus physical storage; schematic only |
| Historical inputs | `figures/05-historical-profiles.png` | Three profile cards combine normalized price paths, activity strips and prominent change rates; visually different prices have similar measured trading activity |
| Main result | `figures/06-historical-ratios.png` | Crossover chart with all 32 observations for the directional/full-grid example; table of median paired ratios across all 12 workloads shows the repeated reversal |
| Compiler explanation | `figures/09-account-state-mechanism.png` | Account-file metaphor: keep one record open as bars advance versus fetch/update/return records for each bar. Show register retention and the 32 B read / 16 B write steady event-first path; static inspected operations, not timings or DRAM traffic |
| Complete cost | `figures/07-historical-whole.png` | Show actual stage costs and all total observations for the predetermined directional/N32768/K64 cell |

All historical plots use the publication's warm paper, upright Georgia headings,
Arial labels and blue/red palette. Color meaning is labelled within each chart.
The contour uses zero-centered unequal numeric ranges, explicitly disclosed;
no hard-coded synthetic return scale or financial winner selection. Raw market
prices remain local. Derived account summaries, all 384 timing observations,
activity aggregates and source hashes are retained alongside the figures/results.

The mechanism illustration was redesigned on 17 November as two account-file
scenes, with the existing warm paper, upright Georgia and blue/red palette.
Both read/write arrows return to account A; B and C show the later accounts.
The sheets and array rows are schematic, not register allocation or a byte scale.
Next: review this replacement in the compiler-explanation passage. No new
measurements are required for the visual change.

The following original specifications describe the development rationale; the
current asset table above governs the manuscript.

The author accepted the replacement designs on 19 November. Profile cards and
the crossover chart now appear in the manuscript, with matching captions and
the same audited evidence. Their maintained renderer is
`analysis/plot_historical_editorial.py`, also called by the full historical
plot pipeline. Next: review the updated complete reading sequence. No additional
timing campaign is needed for these figure changes.

## Editorial question

How do loop order and physical feature layout affect an independently stateful C++ parameter sweep, while preserving its trading decisions and numerical output?

The pilot demonstrates the About promise: investigate a software design choice and its small print through an accessible trading example. The code has a substantive C++ subject: owning storage versus non-owning typed multidimensional views, explicit strides, state lifetime and compiler-visible loop structure. Finance supplies a meaningful stateful workload.

## Proposed article sequence

| Position | Passage | Asset and its distinct job |
| --- | --- | --- |
| Opening | One rule becomes a parameter grid | Figure 1: show what is being computed |
| Strategy explanation | Fast/slow EMA; next-bar decision/execution contract | Short equation and prose; no extra chart by default |
| Loop walkthrough | Follow one column versus one row | Figure 2: explain the mechanism and separate traversal from storage |
| C++ explanation | mdspan layout mappings; four controlled variants | Two small loop snippets and one 2 x 2 design table |
| Evidence | Correctness first, then timings | Figure 3: reveal workload dependence, if any |
| Practical cost | Preparation and replay in the same accounting | Optional Figure 4: show whether a kernel difference matters to the whole run |
| Application | What design decision follows | A bounded conclusion and the parameter-selection limitation |

Aim for about 1,400–1,800 final words, depending on the findings. No introductory glossary, HFT latency claim or full strategy-optimization study is needed.

## Bounded comparison proposal

- One asset, one documented price history, a simple independent long/cash EMA-cross rule, double throughout.
- Implemented grid: 48 distinct EMA spans, 2..96 by 2, with 1,128 valid fast < slow combinations. The bounded synthetic pilot matrix is frozen in `configs/pilot.json`; the separate main campaign completed 576 observations.
- Precompute each distinct EMA once. All variants use identical canonical feature values. No route gets a more efficient indicator algorithm or a different warm-up.
- Logical feature dimensions: [bar, indicator window]. History-contiguous means bar stride 1 (`layout_left`); snapshot-contiguous means window stride 1 (`layout_right`). Layout changes require correct physical materialization, not reinterpretation of the same bytes.
- Four variants: two traversal orders x two feature layouts. Within each layout compare traversal orders; within each order compare layouts. Keep the state structure and config ordering fixed.
- C++23 is justified by mdspan for this new question. It does not alter the standard or build setup of any existing experiment. GCC 16 documentation lists mdspan support; the exact view and its strides now pass locally in `examples/layout.cpp`. The actual engine now passes independent checks. Release compiler diagnostics report no loop vectorization in replay, alongside some vectorized basic-block operations; see `findings.md`.
- Keep AoS/SoA, manual SIMD, threading, alternative strategies, precision comparisons and Ipopt out of the first experiment. Vectorization is an observed compiler outcome, not an assumed treatment.
- Proposed workload variation: a small number of nested configuration counts K and two or three history lengths N. Define the feature population W and its usage explicitly; do not silently change W while attributing the result solely to K. Freeze a bounded matrix after an untimed preflight.
- The common feature set models a reusable research input. For fresh-run totals disclose exactly which features are prepared, their materialization cost, and any reuse assumption. Do not compare one cold fresh run with another route's already-cached preprocessing.

## Metrics

| Metric | Definition | Role |
| --- | --- | --- |
| Replay elapsed time | Wall time to replay all K configs over the same N_eff eligible updates and produce the required per-config summaries | Primary performance observation; retain each process-level sample |
| Nanoseconds per strategy-bar | replay_seconds * 1e9 / (K * N_eff) | Figure 3's comparable work unit; one update includes the same accounting/output work in every route |
| Relative traversal cost | T_strategy_first / T_event_first at matched N/K/W/layout/input | Optional direct annotation: >1 favors event-first, <1 favors strategy-first; never mix denominators/layouts |
| Whole-run elapsed time | Measured complete pipeline, including actual feature preparation/layout materialization, state setup/reset, replay and summary output | Practical result; record excluded disk I/O explicitly if using already-parsed input |
| Stage times | Non-overlapping timed stages from the same complete run | Optional stacked figure; do not add independently aggregated medians and label the sum a measured median total |
| Feature/state/output bytes | N x W x sizeof(double), plus actual state/config/output buffer sizes and any materialization scratch | Context for access-pattern hypotheses; distinct from measured peak RSS |
| Compiler evidence | Vectorization diagnostics and relevant generated code for the exact measured build | Supports a limited explanation; no inferred SIMD or cache events from timing alone |
| Financial outputs | Net period return, trade count, turnover and maximum drawdown under the frozen accounting contract | Output parity; only net return needs a main-text heatmap |
| Correctness | Per-bar target/position/trade trace and per-config result checks against an independent small reference | Required outside timed paths; final P&L alone can hide divergent paths |

For a future equity sequence E_t > 0: net return = E_end/E_start - 1; maximum drawdown = max_t(1 - E_t / max_{u<=t} E_u). Define turnover as sum of absolute traded notional divided by fixed initial capital, if this is the chosen account model. Trading-event counts must define entries/exits separately from round trips. The accounting, fee, warm-up and liquidation rules in `brief.md` are implemented and independently checked. The pilot and main campaign retain all individual timing observations; see findings for the rising-load limitation.

No Sharpe-ratio ranking, p99 timing claim, annualized extrapolation or probabilistic uncertainty band is needed for the pilot. Cross-configuration outcomes share one market history and are not independent market samples. Timing repetitions and input histories must also be identified separately.

## Figure specifications

### 1. A thousand versions of one rule

- One triangular heatmap, fast span on x, slow span on y, same eligible period and initial accounting for every tile.
- Invalid fast >= slow cells are blank, never encoded as a zero-return result.
- A common diverging color scale centered at zero; label it explicitly as net period return. Blue/red here encode the signed financial outcome, separately from traversal colors in later figures.
- Caption: context/output requirement, not evidence of a profitable strategy. Do not print a second identical map merely to show implementation agreement.
- Real figure input: verified per-config results, frozen grid/data/accounting metadata. The original synthetic example remains in `figures/`; the current illustration uses the preselected historical directional/long window.

### 2. Two routes through the same work

- Two event-by-strategy grids: blue down columns, red across rows. Show arrows and initial step numbers.
- Time moves downward within every strategy in both traversals. Independent strategy states are an explicit prerequisite for reordering these updates.
- Beneath the grids, two memory strips contrast a single indicator's history with a single event's indicator snapshot.
- Label as schematic logical operations. These grids are not the EMA feature matrix; name both axes and explicitly distinguish the two matrices.
- Does not depict elapsed time, hardware lanes, CPU cache lines or measured memory traffic.

### 3. What does one strategy-bar cost?

- Two small multiples, one per physical feature layout. Blue strategy-first, red event-first; use circle/square markers as well as color.
- x: K, ordered settings, log scale if broad. y: ns/strategy-bar, lower is better. Fixed N and W within the panels.
- Raw matched process observations plus a specified descriptive center. Lines join measured workload settings, not an inferred smooth law.
- Use a second N only if it changes the practical decision. Do not mark an exact cache threshold from an apparent bend.
- Real figure input: retained individual timing observations and complete provenance. Main inputs are retained in `results/main-observations.csv`; eight observations per candidate/cell/seed, with load variation disclosed.

### 4. Optional: the whole bill

- Four zero-baseline horizontal stacked bars: one per traversal/layout combination at a selected workload.
- Stages: feature preparation/materialization, state setup, replay, summary output. Use muted stages and a traversal-colored replay segment; direct labels separate order/layout.
- For the final figure choose a documented representative complete run (nearest the median total, with selection rule disclosed), and show all complete-run totals separately as dots or a range. Never invent a typical run by splicing independently selected stages.
- Keep only if it changes interpretation. Otherwise report measured totals in a small table and stop at three main figures.

## Preview styling and provenance

Follow the current `publication/visual-style.json`: warm paper #FCE9D7, ink #0F0F0F, blue #003C7F, red #BF0000, thin rules, Georgia upright headings and Arial labels. Use the shared file's current upright typography; this proposal changes no publication styling.

`previews/draw_previews.py` generates a four-card storyboard plus individual PNG/SVG figures. `previews/mock-data.json` contains design-only fabricated values, never measurements. All result-preview assets carry FICTIONAL VALUES / NOT BENCHMARK RESULTS. The traversal diagram is separately labelled schematic. No performance direction, crossover, return surface or stage proportion in a preview is a prediction.

## Status and next step

Two alternative presentations of the full parameter results are generated by
`previews/ema_result_maps.py`: a filled contour map in fast/slow coordinates,
and a scatter plot of net return against maximum drawdown. Both read all 1,128
checked rows from `figures/accounts.csv`. Contours explicitly interpolate between
tested points; the scatter labels fixed 2/4, 10/30 and 32/96 examples. These are
synthetic outcome illustrations, separate from timing evidence. Next: compare
the contour design with the existing heatmap before replacing the article asset.
The author prefers the contour design. Its revised scale keeps zero paper-neutral,
losses red and gains progressively light blue through navy, using fixed 10-point
return bands and a proportional colorbar. Labels on the darker contours are white.
Next: review the revised color treatment before promoting the preview to the article.

An alternative opening preview is available through `previews/ema_walkthrough.py`:
three aligned panels show the 10/30 EMA signal, executed holding periods and
account equity over the first 256 eligible bars of retained seed 11. It uses the
common 96-bar warm-up and includes fees, without forcing liquidation at the
display boundary. Its full-period reference summary is checked against retained
C++ outputs. Unlike the earlier fictional previews, this uses computed synthetic
results. Next: review this walkthrough as the lead illustration, with the full
parameter heatmap reduced to an overview. The manuscript is unchanged pending
that visual review; no benchmark rerun is needed for this illustration.

Status: implemented four-variant engine, independent reference, sixteen strategy tests and passing debug/sanitizer/release checks. The main scale gate passed 72 untimed workers. The pilot completed 192 timing observations and the main run 576; every output check passed. The draft embeds checked accounts, the traversal schematic, the main timing chart and complete-cost chart. Load rose during both measured runs; this limits interpretation. Barrier evidence is unchanged.

Next: review the complete draft and figure sequence, keeping the load limitation beside numerical claims. Decide whether a better-isolated reproduction is needed before release. The current illustration remains synthetic; there is no missing market dataset for this version.

Estimated total author effort: provisionally 15–22 hours including setup, reference checks, implementation, one bounded campaign, interpretation and writing. That is approximately 3–8 weeks at 3–5 hours/week. Reassess after the first small correctness/preflight milestone; this is not a publication-date commitment.
