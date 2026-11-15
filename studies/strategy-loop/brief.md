# Strategy-loop investigation brief

Status, 15 November 2026: article development and layout preflight underway.
The C++23 layout example passes locally; no backtest engine or timing campaign
exists yet. This brief selects working accounting defaults for the first
correctness implementation. Historical data and the timing matrix remain open.

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
- Distinct integer spans >=2, configurations fast<slow, stable lexicographic
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
The checked example is [examples/layout.cpp](examples/layout.cpp). Its success
does not validate the unimplemented backtest or establish abstraction overhead.

No market dataset is needed for the initial correctness gate. Select one before
a historical-return heatmap, and label any larger synthetic performance workload
separately. Do not repeat a short price history and imply it is longer market data.

## Measurement gate, still pending

Primary metrics: whole replay time and replay_ns/(K*(N-L)); retain individual
fresh-process observations with exact inputs, seeds, flags, revision/dirty state,
build/source hashes and compiler diagnostics. Also measure complete preparation,
layout materialization, state setup, replay and summary costs from the same run.
Keep common feature count W explicit while varying configuration count K.
Report conversion scratch and resident buffers, not only nominal matrix bytes.

After all four routes pass an independent oracle, use untimed scale checks to
propose a bounded N/K/W matrix, repetitions, input histories, balanced order,
resource caps and stopping condition. Freeze that plan before timing. No timing
budget or performance direction is selected by this brief.

Initial stopping point: contract documented, exact view checked, and four
efficient variants match independent fixtures before proposing timing.
Only the contract/view portion is complete. Provisional total effort remains
15–22 author hours, approximately 3–8 weeks at 3–5 hours/week; revisit after the
first correctness implementation. See [findings](findings.md) for executed work.
