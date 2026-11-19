# What changes inside the replay loop?

Status, 17 November 2026: the bounded static-analysis stage is complete. The
checked setup cannot currently collect hardware counters; attribution of
runtime remains open. No new timing campaign was run.

## Question and scope

Which differences in the generated code can help explain the observed traversal
ordering, and which runtime causes remain unmeasured? Inspect the existing full
C++23/GCC 16.2 kernel, rather than changing the account contract or constructing
a cheaper competing algorithm. The fixed workload is the directional QQQ window,
N=32,768, W=48, K=1,128, common warm-up 96, capital 1000 and fee 0.0001.

Candidate explanations are feature addressing/reuse, account-state traffic,
branch structure and arithmetic dependencies. None starts as a proven fraction
of elapsed time. Static instructions and architectural load/store operands are
not retired counters, cache misses, memory bandwidth or DRAM bytes.

1. Preserve the measured object and verify that diagnostic compiler output comes
   from an identical object. Inspect all four routes, including startup, common
   unchanged-position paths, transitions and final liquidation.
2. Trace complete steady cash and steady long iterations for each route. These
   paths exclude the first/final bar and outer-loop boundary; report their
   instruction and operand-byte counts explicitly as path-specific analysis.
   Check branch continuity and identify state, feature, bar, rule and config
   accesses. Do not extrapolate one path into a whole-run instruction count.
3. Check native hardware profiling feasibility, bounded to roughly one author
   hour. If available, profile replay separately from preparation; retain event
   definitions, core type, sampling scope and overhead before interpreting it.
4. If usable counters are unavailable, finish the supported static explanation
   and identify the remaining hypotheses. Do not manufacture cache or cycle
   measurements from timings, or install a new toolchain as an implicit step.

The existing machine has only Command Line Tools active. A fresh `xcrun --find
xctrace` fails, the `/usr/bin/xctrace` shim reports that full Xcode is required,
Spotlight finds no indexed Xcode bundle, and `perf` is absent from PATH. These
checks establish no usable counter tool through the checked setup, not the
absence of every possible installation elsewhere. Apple describes this workflow
in [Addressing CPU bottlenecks](https://developer.apple.com/documentation/xcode/addressing-cpu-bottlenecks).

No new elapsed-time campaign is needed to inspect existing instructions. A
counter-enabled follow-up would retain the same outputs and workload, pass
correctness gates after any instrumentation change, use a pilot before its main
plan, and observe the existing quiet/power/resource policies. Feature-only or
precomputed-signal diagnostics would change the work and require separately
labelled interpretations; their times would not be subtracted to assign costs.

## Stopping condition and evidence

Complete an auditable code comparison and a bounded tooling feasibility result.
If counters cannot be collected, the result must say what the code does and
leave the proportion of time spent on each mechanism unresolved. Estimated
hands-on budget is 6–10 hours for the broader counter-assisted investigation;
the static fallback is intentionally smaller. No other extension is selected.

Raw evidence is retained under ignored
`local/evidence/strategy-loop/mechanism-20261117/`. The diagnostic compile,
including optimized-tree and loop reports, produces an object byte-identical to
the previously measured release object:
`7b875f7c0a55018d323e4f9f75dc63fbd380fd5ffcfab92bbc54ee041ab4b9eb`.

## Findings from the actual code

The [path inspector](analysis/inspect_mechanism.py) follows reviewed branch
choices until one full steady iteration closes. It pins the object hash and
rejects unknown objects or unreviewed paths. It does not emulate execution or
infer branch probabilities. Each case assumes an unchanged position, a nonfinal
bar and, for event-first, a nonfinal strategy in the sweep.

| Traversal / storage | Cash-path instructions | Long-path instructions | Account fields read / written inside either path |
| --- | ---: | ---: | ---: |
| Strategy / history | 18 | 20 | 0 B / 0 B |
| Strategy / snapshot | 20 | 23 | 0 B / 0 B |
| Event / history | 29 | 30 | 32 B / 16 B |
| Event / snapshot | 29 | 30 | 32 B / 16 B |

These are counts along particular control-flow paths, not whole-run retired
counts or cycle costs. Operand bytes are not physical memory transactions or
DRAM traffic. Startup, trades, liquidation and outer-loop boundaries differ.

**Account state.** Strategy-first loads the 56-byte account before its bar loop,
keeps its fields in registers and writes the account after its history. History
loads are at object offsets `0xbc0`, `0xbc8`, `0xbcc`, `0xbd0`; stores at
`0xfd0`, `0xfd8`, `0xfdc`, `0xfe0`. Snapshot's general W>1 route does the same
at `0x1464`, `0x146c`, `0x1470`, `0x1474` and
`0x1514`, `0x151c`, `0x1520`, `0x1524`.

In event-first steady paths, account reads are shares (8 B), cash (8 B) and
peak/drawdown (16 B); peak and drawdown are written back (16 B), even without an
opening trade. Each path also reloads 16 B of configuration, 8 B of the fee rule,
16 B of bar prices and 16 B of features. This describes this compiler output;
it does not establish that every reload is unavoidable in other implementations.

**Feature access.** Both read two doubles per update. Coordinate spacing is:

| Physical layout | Adjacent bars for one window | Adjacent windows at one bar |
| --- | ---: | ---: |
| History, N=32,768 | 8 B | 262,144 B |
| Snapshot, W=48 | 384 B | 8 B |

Event-first visits configuration pairs; these are not necessarily the strides
between successive loads. Many pairs reuse the same fast EMA. Snapshot stores
the 48 distinct features for one event in 384 contiguous bytes; history spreads
them across the 12 MiB table. Event/history uses two `madd` instructions for the
feature indices (`0xf18`, `0xf1c`); event/snapshot uses two `add` instructions
(`0xe2c`, `0xe30`). Cache behaviour and relative instruction costs remain unmeasured.

**Arithmetic and branches.** Every reviewed path includes one scalar `fdiv` for
drawdown. A no-trade bar still marks equity and updates the peak and maximum
drawdown. The directional/full-grid activity report has 21.16 opening changes
per 1,000 updates, making unchanged-position paths relevant; that report is not
an instruction-path histogram and treats final liquidation separately. GCC emits
a shorter steady-cash path for strategy/history that loads only the bar close.
Strategy/snapshot's general path loads open and close. Its separate W=1
specialization is unused by the 48-window workload. The diagnostic loop report
confirms stride-based loop versioning and zero vectorized replay loops; some
basic-block operations are vectorized as previously documented.

**Interpretation.** Register use, explicit memory operations, addressing and
control flow differ, so a cache-only explanation would be incomplete. State
traffic alone does not settle the result either: event/snapshot has more
instructions on these steady paths, yet its historical prepared median was
lower than strategy/snapshot. That reversal is consistent with the relevance
of data access/reuse, but it does not establish cache misses or the proportion
of runtime attributable to any mechanism.

## Validation, reproduction and next step

Debug configure/build/CTest passed all six entries, including 33 strategy tests
and real-history excerpts. New checks verify branch targets versus fallthrough,
rejection of unreviewed control flow and scalar/pair/vector operand widths.
The C++ engine did not change; no new sanitizer run is claimed for this
analysis-only stage. Original and diagnostic object hashes were checked.

```sh
.venv/bin/python studies/01-strategy-loop/analysis/inspect_mechanism.py \
  --object local/evidence/strategy-loop/mechanism-20261117/diagnostic-replay.o \
  --output build/mechanism-inspection
MPLCONFIGDIR=build/matplotlib XDG_CACHE_HOME=build/cache .venv/bin/python \
  studies/01-strategy-loop/analysis/plot_mechanism.py --output build/mechanism-figures
```

Use a new inspection output directory. Paths must be reviewed again if the
pinned object changes. The [public path record](results/mechanism-paths.json)
omits private command paths; the original raw report remains unchanged. The
[illustration](figures/09-account-state-mechanism.png) explains inspected
operations, not new timing results.

The static fallback stopping condition is met. Next is author review of the
explanation. To attribute cycles, cache events or branch misses, obtain usable
Xcode/Instruments with confirmed M3 counter coverage, or a suitable native
profiling host. Check availability and permissions before freezing a counter
pilot. No tool installation or other mechanism experiment has been started.
