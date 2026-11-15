# Strategy-loop experiment proposal

Status, 15 November 2026: preliminary design, not a frozen or executed campaign.
The [article](article.md) and [figure plan](figure-plan.md) develop the question.

## Question and comparison

For independent long/cash EMA-cross strategies using the same history, compare
strategy-first and event-first traversal, crossed with history-contiguous and
snapshot-contiguous features. Each strategy must see bars chronologically.
Exclude shared capital, cross-strategy fills or shared mutable behavior that
would invalidate reordering.

Precompute each distinct EMA once for all variants. Use identical canonical
features, states, arithmetic, configuration order and outputs. Proposed C++23
`std::mdspan` expresses a non-owning [bar, window] view; its layout must match
the physical buffer. Exact local support is unverified.

## Decisions required before implementation

- Select one instrument, a licensed documented dataset/period and deterministic
  synthetic fixtures for independent checks.
- Freeze EMA spans, initialization, warm-up, equality behavior, signal timing,
  next-bar execution, sizing, costs, financing and final-position treatment.
- Define eligible updates, per-bar decisions/positions/trades and per-configuration
  outputs. Check an independent reference; final P&L alone is insufficient.
- Freeze a small matrix of history length N, configuration count K and feature
  count W. Keep W explicit when varying K. Estimate memory and runtime first.
- Check the actual toolchain and compiler diagnostics; do not assume vectorization.

## Evidence and boundaries

Primary metrics are complete replay time and nanoseconds per strategy-bar,
retaining individual process observations. Also measure complete-run preparation,
state setup, replay and summary; never splice phase medians into a fictitious
total. Record feature/state/output bytes separately from RSS.

The parameter heatmap explains the workload, not profitability. A historical
parameter search does not establish out-of-sample performance. Explicit SIMD,
threading, AoS/SoA variation, precision changes, live execution and tail-latency
claims are outside this first scope.

Initial stopping point: the contract is frozen, the exact view compiles, and four
efficient variants match independent fixtures before proposing timed work.
Provisional total effort: 15–22 author hours, roughly 3–8 weeks at 3–5 hours/week.
Reassess after the first correctness milestone. Supporting primary references
and unresolved writing passages are in the article and figure plan.
