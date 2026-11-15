# Barrier-option SIMD — fixed groups or lane refill?

Status, 14 November 2026: the bounded main campaign and descriptive analysis are complete: 324 prepared-input and 324 complete-valuation observations, all audited. Correctness, sanitizers, 138 independent verification cases, runner smoke and all eleven runner/analysis tests passed. Figures, full timing tables and a chronological diagnostic are prepared. Refill's nearly full logical occupancy did not yield a uniform runtime improvement; increased system load and observed variation limit precise performance claims. Figure/claim review and article integration remain. See findings.md for details.

## Question

For identical discretely monitored knock-out paths and payoffs, when does replacing finished SIMD lanes save more time than its input access and bookkeeping cost?

The hypothesis is that path lifetimes affect the preferred execution policy. A null result is useful. No universal SIMD benefit, novel refill algorithm or production-pricing equivalence is assumed.

Background: NVIDIA's [Accelerating Python for Exotic Option Pricing](https://developer.nvidia.com/blog/accelerating-python-for-exotic-option-pricing/), 19 March 2020, uses early exit in GPU simulation. It does not establish CPU performance. [P1928R15](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2024/p1928r15.pdf), 22 November 2024, describes data-parallel interfaces, not a speed guarantee. This implementation uses the Parallelism TS in `std::experimental`, not C++26 `<simd>`.

CPU refill is established prior work: Lang et al., [Make the most out of your SIMD investments](https://d-nb.info/1202257798/34), 2019, study AVX-512 database pipelines, including refill overhead and workload dependence. Our bounded contribution is a reproducible option-path comparison on native two-double ARM SIMD, including path identity, layout and complete generation-plus-valuation cost.

## Contract and equal outputs

- One thread, binary64; zero-rebate, discretely monitored up-and-out European call.
- Spot 100, strike 100, maturity one year, rate .02, dividend yield 0, volatility .20; 252 dates through maturity. Initial or monitored spot at/above the barrier permanently knocks out the option.
- Surviving payoff: `exp(-r*T) * max(S_T-K, 0)`. Every method overwrites every payoff in original path-ID order and uses the same ascending-ID scalar aggregation.
- Risk-neutral GBM multipliers: `exp((r-q-.5*sigma*sigma)*dt + sigma*sqrt(dt)*Z)`. Canonical binary64 arrays, PCG64/NumPy, seeds 11, 29, 47, path-major chunks of at most 4096 paths. Retain exact inputs and hashes; a seed alone is insufficient.
- Barriers 105, 120, 150. Pilot: 8192 paths; completed main: 100000. Inputs are synthetic pricing scenarios, not market forecasts.
- Validate dimensions, parameters, every multiplier and reachable numeric range outside timing. Infinite barrier is allowed for the vanilla check. Overflow and underflow to zero fail explicitly.

## Methods and layouts

1. Scalar early exit, ordinary `-O3` optimizations enabled.
2. Native SIMD fixed groups, masking completed lanes until the group finishes; safe partial final groups.
3. Simple refill: each finished lane takes the next unstarted path, with that path's date reset to zero. Indices, input gathering, output scattering and bookkeeping are included.

All three run with identical physical input in each of two layouts: path-major (primary) and step-major (robustness). Neither layout is selected after seeing a favorable result. Refill uses per-lane path/date indices; it cannot inherit the previous path's random stream.

## Gates and timing scopes

Literal payoff/date fixtures, exact barrier hits, permanent knock-out, initial knock-out, vanilla, deterministic volatility, monotonicity, invalid inputs and vector-tail boundaries precede timing. A separate date-wise NumPy oracle checks every payoff and stopping decision; exact Decimal fixtures audit that oracle. Debug and ASan/UBSan exercise the actual C++ pricer.

Prepared-input scope includes kernel, all output writes and common aggregation. Allocation, input generation, input validation and diagnostics are outside that interval. A separate template instantiation collects logical lane work without adding counters to timing.

Complete-valuation scope includes RNG construction, NumPy canonical allocation/generation, required layout conversion/allocation, output allocation, ctypes bridge, kernel and aggregation in one in-process interval. Imports, library loading, parameter constants, correctness checks, serialization and buffer destruction are outside. It is the defined Python/C++ valuation pipeline, not an all-C++ production service. Phase timestamps add small overhead; no clock-overhead subtraction is applied.

The pilot fixes 3 process repeats per seed/barrier/layout/method, one warm-up per scope, and cyclic method order to balance position. The scopes use separate sequential processes: 162 observations in each scope, 324 pricing processes. No simultaneous benchmarks, compilation or plotting.

## Limits and stopping condition

No continuous monitoring, Brownian bridge, rebates, Greeks, live data, network latency, concurrency, wider packs, float precision or alternative pricing models. No inference of hardware causes from wall time alone.

Initial stopping condition: equal-output implementations verified, bounded pilot retained, and a concrete main-campaign decision. This condition is met. The subsequently authorized main campaign used six balanced repeats per seed/case and the unchanged methods. All retained observations have now been analyzed, with per-seed variation, full ranges, matched comparisons and environment limits. Next: review the prepared figures and bounded claim for article integration. No additional timing campaign is required by the completed checks; do not add repetitions based on the observed rankings.

## Precision extension, 14 November

The author subsequently requested runnable float/double comparison code. The
separate [precision extension](precision/README.md) now provides a native-float
implementation, correctness/reference checks, a frozen prepared-input pilot and
analysis. Its [brief](precision/brief.md) defines the changed numerical contract.
The original double pricing sources and historical observations remain intact.
The original investigation's completion above does not describe the new
precision pilot as executed. Its timing run remains pending a quiet window.
