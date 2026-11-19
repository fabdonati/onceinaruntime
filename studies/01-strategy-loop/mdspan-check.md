# Bounded mdspan access check

Status, 17 November 2026: complete. Debug, ASan/UBSan, eight full-size output
checks and a 32-observation pilot passed. Manual indexing saves no instructions
in the inspected replay; the pilot's rising background load prevents a precise
timing-overhead conclusion. The historical replay campaign and its archived
evidence remain unchanged. Other follow-up options remain proposals.

## Question and stopping condition

Does the existing use of C++23 `std::mdspan` generate additional replay work
compared with the corresponding manual offsets? This is an independent question
about the existing kernel, not a claim of new layout or trading research.

Build the same complete engine twice: default `mdspan` and
`OIR_STRATEGY_MANUAL_INDEX=1`. Only the feature lookup differs:
`features[t,w]` versus `data[t + N*w]` (history) or `data[t*W + w]` (snapshot).
Both retain dynamic extents, compile-time mappings, ordinary aliasing, inlining
opportunities, double precision, account lifetimes and all ordered outputs.
Small local access lambdas are inlineable in both versions. The build selector
is compile-time; no access-mode branch is added to replay.

Use the existing GCC 16.2 release settings: `-O3 -DNDEBUG -std=c++23
-fno-fast-math -ffp-contract=off`. C++23 is the established exception for this
study because it uses standard `mdspan`; other experiments remain unchanged.
Do not give either version restricted pointers, fixed extents or a separately
optimized algorithm. Separate binaries avoid introducing extra runtime dispatch.

Correctness: run the independent Python oracle and trace/no-trace boundary
fixtures against both builds, including empty eligible ranges, odd counts,
final liquidation and real overnight excerpts. Run debug and ASan/UBSan checks.
Then check all eight access/order/layout combinations on the predetermined
directional QQQ window, N=32,768, W=48, K=1,128, warm-up=96, capital=1000,
fee=0.0001. Compare every ordered summary with the retained independent oracle
and check identical C++ outputs. No trace collection or timings in this gate.

Inspect optimized object code for the full replay, including both traversals
and mappings. Retain raw disassembly, object bytes, relocation information,
compiler commands, revision/dirty state and source snapshots. Compare the
default build against the previously measured build as a regression check.
Equivalent replay code answers this bounded instruction-overhead question;
timing is optional in that case. If code differs, inspect the difference before
deciding whether a paired timing pilot is informative. Any pilot is capped at
15 minutes and uses the existing quiet-entry and actual-power recording rules.

Supported claims must name the compiler, flags, mappings and kernel. Matching
code does not establish all uses of `mdspan` are free, nor explain cache effects
or demonstrate live trading latency. No hardware counters, new market data or
financial robustness tests are included. Planned author effort: 2–4 hours.

Initial code inspection found unchanged address calculations and a small number
of operand-order/condition-code differences elsewhere. A descriptive pilot is
therefore selected: four paired fresh-process repetitions for each of the four
traversal/layout combinations, 32 observations total. Alternate mdspan/manual
versus manual/mdspan within each pair; use the existing four-row balanced order
for traversal/layout candidates. No additional replay warm-up. Keep every sample
and report replay and prepared intervals separately. The gate requires 60 seconds
of sampled load no greater than half the logical CPU count, within 600 seconds;
whole campaign cap 900 seconds, each worker 30 seconds, RSS 512 MiB, evidence
256 MiB, free disk reserve 1 GiB. Record and retain actual stable AC/battery mode;
battery operation is authorized. This small pilot cannot prove statistical
equivalence or justify a numerical universal-overhead claim. No main timing
campaign is selected.

Reproduce the full-size gate and pilot after debug/sanitizer checks:

```sh
.venv/bin/python studies/01-strategy-loop/analysis/check_mdspan.py \
  --verified local/evidence/strategy-loop/historical-20261117/verification \
  --output local/evidence/strategy-loop/mdspan-20261117/comparison \
  --pilot --allow-battery
```

The output directory must not exist; use a new one for any later rerun. Source
bars and the hash-checked independent oracle remain local. Omit `--pilot` to
repeat only code inspection and the untimed full-size gate.

## Evidence

Both complete non-diagnostic replay functions contain **645 static instructions**
covering all four traversal/layout routes, at identical offsets and with equal
mnemonic counts. This is a function-size count, not retired instructions per
update. Eleven encodings differ: four floating-point multiply operand swaps,
three equality/inequality comparison operand swaps, and two reversed floating
comparisons with matching select-condition changes (`gt` to `mi`). Every other
replay instruction, including address calculations, loads, stores and branch
targets, is identical. The two objects are therefore not byte-identical.

The default mdspan object **is byte-identical to the original measured object**:
`7b875f7c0a55018d323e4f9f75dc63fbd380fd5ffcfab92bbc54ee041ab4b9eb`.
The manual object is
`aa0de4baa77932003629f6478034fdfe846b7784ec88b4f3197a80c0baa55e2a`.
The extra local access lambda has not changed the default release object.

Debug and sanitizer configure/build/CTest passed all six entries, with the real
historical fixture enabled. Both trace and non-trace access variants match the
independent oracle on the boundary fixtures. All eight full-size runs and all
32 pilot runs produced identical ordered summaries for every one of the 1,128
accounts, also matching the retained independent ledger within its documented
tolerance. The input and reference hashes are checked before execution and at
completion; the actual source/build snapshots are retained.

The first attempt completed its eight untimed workers, then stopped before
timing because the reused power parser did not accept macOS's `finishing charge`
status on AC. That record remains under `comparison/`. The parser fix has a
regression check. The separate `comparison-ac/` run waited 120.243 seconds to
establish 60 seconds of low sampled load and completed in 124.765 seconds total.
All power samples report AC. Load rose from 3.286 to 9.669 during measurement;
the before/after process snapshots include other active system processes. No
processes were stopped, and no samples were removed or replaced. This does not
identify which process caused any individual timing difference.

The clock's smallest positive consecutive-read delta was 1 microsecond; many
reads shared a timestamp. Peak worker RSS was 36,847,616 bytes. Four paired
observations per route are descriptive, and this pilot is not an equivalence
test. See the [curated results](results/mdspan-summary.json) and
[all timing observations](results/mdspan-pilot-observations.csv). The noisy
timing evidence does not establish a precise percentage overhead or savings.

Raw checks, commands, disassembly, relocations, source archive, objects, binaries,
summaries and individual observations remain under ignored
`local/evidence/strategy-loop/mdspan-20261117/`. The stopping condition is met:
manual indexing supplies no instruction savings for this compiled replay.
No further timing campaign is needed for that bounded claim. Review the short
article addition; hardware mechanisms and other follow-ups remain unselected.
