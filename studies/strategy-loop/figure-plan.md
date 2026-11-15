# Article and figure plan

Updated 16 November 2026. The engine and independent accounting checks now pass, including the untimed scale matrix. The article contains a checked synthetic account heatmap and the traversal schematic. The completed 576-observation main run supplies performance charts, with the recorded host-load limitation beside the claims. `previews/figures/` contains the earlier fictional return/timing designs; the traversal image is separately labelled schematic.

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
- Real figure input: verified per-config results, frozen grid/data/accounting metadata. The checked synthetic example is in `figures/`; no observed-market input is selected.

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

Status: implemented four-variant engine, independent reference, sixteen strategy tests and passing debug/sanitizer/release checks. The main scale gate passed 72 untimed workers. The pilot completed 192 timing observations and the main run 576; every output check passed. The draft embeds checked accounts, the traversal schematic, the main timing chart and complete-cost chart. Load rose during both measured runs; this limits interpretation. Barrier evidence is unchanged.

Next: review the complete draft and figure sequence, keeping the load limitation beside numerical claims. Decide whether a better-isolated reproduction is needed before release. The current illustration remains synthetic; there is no missing market dataset for this version.

Estimated total author effort: provisionally 15–22 hours including setup, reference checks, implementation, one bounded campaign, interpretation and writing. That is approximately 3–8 weeks at 3–5 hours/week. Reassess after the first small correctness/preflight milestone; this is not a publication-date commitment.
