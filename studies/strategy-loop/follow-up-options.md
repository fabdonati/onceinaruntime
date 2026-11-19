# Follow-up questions after the historical replay study

Status, 17 November 2026: the [abstraction check](mdspan-check.md) is complete.
The subsequently selected [mechanism check](mechanism-check.md) completed its
static stage; counter attribution needs usable profiling tools. Streaming and
financial robustness remain proposals. Original traversal/layout results are
unchanged; selecting one extension does not imply selecting all of them.

## Recommendation and scope

First check whether the multidimensional view changes the generated replay code.
Then investigate the mechanism behind the traversal/layout ordering, provided
hardware profiling is feasible. These two extensions can strengthen the current
article. Streaming response latency and strategy robustness each deserve a
separate brief and article, with a different measurement contract.

Author-effort estimates below are planning estimates, not elapsed benchmark
durations. At 3–5 hours per week, the first two together represent approximately
2–5 weeks, with a tooling feasibility stop before committing to counter work.

| Question | Smallest useful experiment | Evidence and figure | Estimated hands-on effort |
| --- | --- | --- | --- |
| Does `mdspan` add overhead here? | Same full kernel, buffer, layout and traversal; replace only view access with the corresponding manual offset | Generated hot-loop code; if necessary, paired timing differences around zero | 2–4 hours |
| What explains the ordering? | Inspect state loads/stores and indexing; profile the four full kernels; add narrowly scoped diagnostics for competing mechanisms | Instructions/cycles per update, supported memory/branch events, working-set response; aligned metric panels | 6–10 hours including a bounded tool check; installation may add time |
| How quickly can a streaming engine react? | Incremental causal feature updates; compare immediate processing with bounded batching under scheduled steady and bursty arrivals | Arrival-to-decision latency distribution, queue depth, missed deadlines and throughput | 10–16 hours for a local prototype; production transport is a further project |
| Do selected EMA settings survive unseen prices and costs? | Freeze selection and cost assumptions, then chronological walk-forward evaluation with an untouched final period | Out-of-sample performance, drawdown, turnover, cost sensitivity and parameter stability | 8–15 hours for a bar-based robustness study; quote-based execution realism adds work |

## 1. Abstraction cost

Completed: both full replay functions contain 645 static instructions, with
identical address calculations and memory operations. Eleven instructions differ
only in operand order and matching comparison conditions. Debug/sanitizer,
eight full-size gates and a 32-observation pilot passed. Rising pilot load means
no precise timing percentage is supported. See [the protocol and evidence](mdspan-check.md).

Keep the same runtime extents, compile-time layout choice, compiler/flags,
aliasing information, account-state lifetime, inlining opportunities, arithmetic
and required ordered outputs. Compare `features[t,w]` with `buffer[t + N*w]` or
`buffer[t*W + w]`, respectively. Giving only the manual version a restricted
pointer, static extent or precomputed offset would test more than the abstraction.

Start with one predetermined historical workload and inspect the optimized
full replay specializations. If the compiler emits equivalent hot loops, retain
the disassembly and scope the finding to that build. Timing need not manufacture
a visible difference. If code differs, explain the difference and run a bounded
paired pilot before freezing a timing matrix. Preserve output parity through
debug, sanitizer and independent-reference checks after C++ changes.

Possible supported conclusion: this use of the default `mdspan` accessor and
these two mappings introduces no additional hot-loop instructions in this
compiler/build, or a specific additional cost is observed. A small timing
difference alone does not prove universal zero overhead.

The [mdspan design paper](https://arxiv.org/abs/2010.06474), submitted in 2020,
includes zero-overhead experiments for its implementation. It motivates the
question; it does not establish the outcome for this GCC build or kernel.

## 2. Mechanism behind the traversal/layout result

Static stage complete: the compiled steady paths show register-resident state
for strategy-first and 32 B read / 16 B written per unchanged event-first update.
Feature addressing and branch paths differ too. Hardware counters could not be
collected through the checked setup. The [audited paths and illustration](mechanism-check.md)
support the narrower explanation; cache and cycle attribution remains open.

The current code already suggests competing hypotheses:

- Feature stride and reuse differ with traversal and physical layout.
- Strategy-first copies one account into a local variable for its whole history;
  event-first updates `states[s]` repeatedly. Registers and state load/store
  traffic may therefore matter alongside feature-cache behaviour.
- Instruction count, address calculations and branch behaviour may also differ.

First inspect the compiler output for those distinctions. Profile the four
unchanged full kernels on the same predetermined directional/long workload.
Separate replay from preparation and summary construction. Retain counter event
definitions, collection scope, core type, available multiplexing/scaling details
and profiler overhead. A process-wide counter total dominated by preparation
cannot explain the replay interval.

Where the available events support it, report cycles and retired instructions
per strategy-bar, memory/cache events per unit of work and branch misses per
branch or per thousand updates. Do not label a generic memory-stall metric as
an L1 miss count. Observe core migration and heterogeneous-core effects rather
than assuming the same counter interpretation across all cores.

Only then add diagnostics that distinguish hypotheses: feature traversal with
a consumed checksum, state updates driven by precomputed identical targets,
and a predeclared working-set sweep. These intentionally change the work and
must be labelled mechanism probes, not alternative implementations of the full
benchmark. Their timings are not additive; subtracting them does not assign a
percentage of full runtime to caches. Changing N or K in the financial model
also changes activity and configuration population, so it is not a pure cache
capacity intervention.

A supported result needs agreement between code inspection, counters and a
targeted intervention. If evidence is mixed, retain competing explanations.
Counter correlation alone does not establish that cache misses caused the
entire timing difference.

Local read-only feasibility check on 17 November: active developer directory is
`/Library/Developer/CommandLineTools`; `g++-16` and `llvm-objdump` are available;
`xcrun --find xctrace` fails, and `perf` is absent from PATH. Therefore assembly
inspection can start with the existing setup. Apple documents CPU bottleneck
investigation through Instruments' CPU Counters template in
[Addressing CPU bottlenecks](https://developer.apple.com/documentation/xcode/addressing-cpu-bottlenecks).
Its availability and relevant event coverage on this M3 remain to be verified
with a usable Xcode/Instruments installation. No tool installation or system
configuration change was made. A native Linux host with supported counters is
another possible environment; a VM is not assumed to expose the host PMU.

Stop the feasibility stage after roughly one author hour if useful counters
cannot be collected. An assembly-based explanation with explicit remaining
hypotheses is a valid narrower outcome.

## 3. Streaming response latency

The present full-history strategy-first loop is not directly an online
competitor: a running strategy cannot consume future events before they arrive.
The new contract must process only available messages and maintain incremental
EMA/state. Begin with a local input-to-decision path; define whether the endpoint
is the first decision or completion of all K strategy decisions for that event.

Compare immediate processing with small fixed batches plus a bounded flush
timeout. Include time waiting for a batch, queueing and processing in response
latency. Keep final states and ordered decisions equivalent for independent
accounts. Measure throughput separately from per-event service time and
arrival-to-decision latency. Use a logical replay clock for event semantics and
a separate monotonic wall clock for processing measurements.

The current minute bars can exercise the code and accounting. Accelerating them
produces an explicitly synthetic arrival workload, not observed HFT traffic.
Realistic market microstructure would require appropriate timestamped quotes or
trades; order-book/exchange execution adds still more scope.

Schedule arrivals independently of consumer completion, preserve late arrivals,
record intended arrival, enqueue, start and completion timestamps, and report
generator lateness. This avoids hiding queue delays during slow periods. The
[HdrHistogram measurement discussion](https://github.com/HdrHistogram/HdrHistogram#corrected-vs-raw-value-recording-calls)
illustrates how missed observations can make a latency distribution look better
than what an arriving request experiences; adopting that dependency is optional.

Calibrate clock resolution and recording overhead first. Choose event counts
and independent repetitions after a bounded pilot. Show p50/p95/p99 only with
the number of observations and run structure; p99.9 needs adequate tail support.
An exceedance curve and latency-versus-offered-load panel would reveal a
throughput/response-time tradeoff. Production wire-to-order claims require a
defined feed/NIC/network/order path and suitable timestamping, absent here.

## 4. Financial robustness

The current three windows were selected by price characteristics and their
account outcomes have already been inspected. They are exploratory evidence,
not a pristine final financial test set. Before additional selection, freeze
the objective, eligible parameter population, chronological training/validation
rules, fees, cost scenarios and comparison with buy-and-hold/cash. Reserve an
unexamined final period or collect a genuinely prospective one.

Use preceding data to warm indicators without leaking future values. Specify
account/position handling at each evaluation boundary and how an updated
parameter choice is executed. Model split/share changes and dividends
consistently before claiming total-return performance; the present model is
price-only. Add spread/slippage/delay sensitivity as explicit assumptions, not
as observed fills derived from minute OHLC bars.

Report held-out returns, drawdown, turnover, trading costs and parameter
stability; use comparisons appropriate to differing market exposure. Record
every tried selection rule and cost model. Dependence and repeated model
selection complicate uncertainty: one holdout or a high Sharpe ratio alone
does not settle robustness. Bailey et al.'s
[*The Probability of Backtest Overfitting*](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf)
(February 2015) directly discusses multiple strategy trials, including moving
average selection.

A useful first question is whether apparent settings remain attractive after
chronological evaluation and modest costs. A rank-change or training-versus-test
plot, accompanied by a cost-sensitivity curve, could communicate the answer.
Losses or unstable rankings are valid findings. Executable profitability would
need a more realistic execution/data contract and further independent evidence.

## Next decision

The abstraction and static mechanism checks have reached their stopping
conditions. Review their additions to the article. Hardware-counter attribution
requires a usable profiling environment; streaming and financial robustness
remain separate proposals.
