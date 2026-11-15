# Strategy-loop investigation brief

Status, 16 November 2026: the accounting reference, four C++23 replay variants,
full-trace fixtures and larger untimed summary checks pass. The accounting
defaults below are implemented. A bounded synthetic timing pilot is frozen in
[configs/pilot.json](configs/pilot.json) completed all 192 observations after an
initial launch was held at the load gate. A separate frozen
[main matrix](configs/main.json) completed 576 observations after its quiet entry
gate passed. Background load rose during both runs; report the resulting limits.
The current study uses identified synthetic input and no historical-market data.

## Question and contribution

For independent long/cash EMA-cross configurations, compare strategy-first and
event-first traversal crossed with history-contiguous and snapshot-contiguous
features. Preserve every strategy's chronological decisions and outputs.
The contribution will be the equal-output stateful comparison, with preparation
cost and compiler evidence, rather than a claim that loop interchange is new.

Exclude shared capital, competition for fills, explicit SIMD, threading,
AoS/SoA changes, alternative trading rules and precision changes. No production
HFT or trading-profitability claim follows from this replay experiment.

## Working accounting contract

- Input: ordered bars with finite strictly positive open and close, and strictly
  increasing timestamps. The first implementation uses deterministic synthetic
  fixtures. Real data needs a documented instrument, provider, period, interval
  and consistent corporate-action/price convention before use.
- `EMA[0,w] = close[0]`. Thereafter `alpha=2/(span+1)` and
  `EMA[t,w]=alpha*close[t]+(1-alpha)*EMA[t-1,w]`, double throughout. Compute each
  distinct window once; every variant consumes identical feature values.
- Strictly increasing distinct integer spans >=2, configurations fast<slow, stable lexicographic
  order. Let L be the largest span in the common feature set. Use bars 0..L-1
  as common warm-up for every configuration, and first execute at open[L].
  The first pending signal comes from close[L-1]. No configuration gets extra
  trading time because its own windows are shorter. If N<=L, reject a timed
  workload; correctness checks may explicitly exercise an empty replay.
- Independent account per configuration: initial capital 1000, cash only,
  zero interest, no borrowing/shorting/dividends, fractional holdings, no lot
  rounding. Target long if fast EMA > slow EMA, otherwise cash; equality means
  cash. A signal at close[t] affects open[t+1], never open[t].
- At an opening transition to long, shares=cash/(open*(1+c)), cash=0.
  At a transition to cash, cash=shares*open*(1-c), shares=0. Fee c=0.0001
  (one basis point of traded notional per side), a toy assumption rather than
  an estimate of actual execution. An unchanged target does not rebalance.
- Mark account equity at each eligible close. On the last close, liquidate any
  remaining holding at that close with the same proportional fee, count that
  sale and replace the last equity observation with post-liquidation equity.
  The final close generates no executable next-bar signal.
- Per configuration: final cash, net period return, number of buy/sell events,
  turnover (sum absolute traded notional / initial capital) and max close-to-close
  drawdown including initial capital in the running peak. The final liquidation
  is a trade event, not an extra replay bar. These simplified marks omit
  intrabar drawdown, spread, impact and funding.

## Equal work and independent checks

Each route processes N-L eligible updates per configuration, writes the same
ordered summaries and retains the same arithmetic sequence within an account.
The four routes share one state-transition definition. A separate small Python
reference and hand-worked fixtures check signals, quantities, cash, fees, equity,
trade counts and summaries outside timing. C++ debug and sanitizer checks precede
any optimized timing. Full trace diagnostics are outside timed paths; summaries
and their updates are part of the required timed work for every route.

Required fixtures: flat/equal indicators; one entry/exit; overnight gap; no
trades; final liquidation; fee arithmetic; common warm-up boundary; empty
configuration set; invalid spans/prices/timestamps; odd configuration counts;
both physical mappings. Check feature identities independently before replays.

## Layout and implementation scope

Logical feature shape is [bar, window]. `layout_left` has offsets t+N*w;
`layout_right` has t*W+w. Materialize buffers to match their mappings. Ownership
and view lifetime remain explicit; changing a view does not transpose data.
The checked example is [examples/layout.cpp](examples/layout.cpp). The engine
checks are separate; neither establishes abstraction overhead.

No market dataset is needed for the initial correctness gate. Select one before
a historical-return heatmap, and label any larger synthetic performance workload
separately. Do not repeat a short price history and imply it is longer market data.

## Measurement gate

Primary metrics: replay plus summary construction, and prepared_ns/(K*(N-L)); retain individual
fresh-process observations with exact inputs, seeds, flags, revision/dirty state,
build/source hashes and compiler diagnostics. Also measure complete preparation,
layout materialization, state setup, replay and summary construction from the same run.
CSV input, validation, configuration selection and CSV output are outside that
complete computation interval; [benchmark.md](benchmark.md) defines the boundaries.
Keep common feature count W explicit while varying configuration count K.
Report conversion scratch and resident buffers, not only nominal matrix bytes.

The independent oracle and scale gates have passed. The frozen pilot uses
N={4096,32768}, W=48, K={64,256,1128}, seeds={11,29}, and four fresh-process
repetitions in balanced order for every candidate: 192 observations. The maximum
campaign duration is 15 minutes; memory, disk, entry conditions and failure
stopping rules are in the [run guide](benchmark.md). It characterizes duration
and variation before a main plan; no performance direction is assumed.

Initial stopping point: contract documented, exact view checked, and four
efficient variants match independent fixtures before proposing timing.
The correctness, pilot and bounded main stopping points are met. The executed
main campaign is recorded in [measurement-plan.md](measurement-plan.md).
Historical-market selection and a main campaign are not silently inferred from
the synthetic correctness results. Remaining author work is primarily reviewing
the model/walkthrough, interpreting valid timings and finishing the manuscript.
See [findings](findings.md) for executed work.
