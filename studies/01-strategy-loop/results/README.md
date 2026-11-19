# Strategy-loop results

## Static mechanism inspection

The [mechanism report](../mechanism-check.md) explains the reviewed steady paths
from the actual measured compiler object. [mechanism-paths.json](mechanism-paths.json)
retains path instructions, branch assumptions, memory operands and hashes.
These are static counts and operand bytes, not new timings, hardware counters
or DRAM traffic. The [account-state illustration](../figures/09-account-state-mechanism.png)
is derived from that record. Hardware-counter attribution remains open.

## Separate mdspan/manual-indexing check

The [bounded access comparison](../mdspan-check.md), completed 17 November 2026,
has separate [code/timing evidence](mdspan-summary.json) and
[all 32 pilot observations](mdspan-pilot-observations.csv). Both complete replay
functions contain 645 static instructions; addressing and memory operations match.
The pilot encountered rising background load and does not establish a precise
overhead percentage. These observations are not pooled with the original
traversal/layout campaigns below, whose plots and raw archives are unchanged.

## Historical QQQ campaign, 17 November 2026

The current article uses the **384-observation historical main campaign** after
48 independent untimed checks and a separate 48-observation pilot. Every required
output passed; the four candidates agreed byte-for-byte at matching workloads.
Actual power was AC throughout, with main measurement load 1.977–2.140 after
the quiet entry gate. Keep these observations separate from synthetic runs below.

- [Individual historical observations](historical-observations.csv): all 384,
  with dataset/profile, execution order, stage times and summary hashes.
- [Historical summary and provenance](historical-summary.json): 48 candidate/cell
  groups, absolute min/median/max prepared times, complete medians, all paired
  timing ratios, input/campaign/analysis hashes and twelve activity cells.
- [Historical profile/activity figure](../figures/05-historical-profiles.png),
  [timing ratios](../figures/06-historical-ratios.png),
  [complete computation](../figures/07-historical-whole.png),
  [account contours](../figures/08-historical-accounts.png).
- [Derived account summaries](../figures/historical-accounts.csv) for the
  predetermined directional/long illustration, including every EMA pair.

Original exports and all campaign evidence remain local. The archive at
`local/evidence/strategy-loop/historical-20261117/` retains verification,
separate pilot/main directories, monitoring and all source/build/reference
snapshots; 1,346 pilot/main copied files were hash checked. Curated exports omit
local command paths; original manifests remain untouched. No raw market CSV is
included in these tracked results. See [findings](../findings.md) for limits and
[benchmark instructions](../benchmark.md) for reproduction.

## Original synthetic main campaign

The main campaign completed all **576 observations** on 16 November 2026 local
time. Its configuration was frozen after the pilot: same N/K/W and account model,
three seeds (11/29/47), eight fresh processes per candidate/cell in two balanced
cycles. All ordered outputs passed the independent reference checks and were
byte-identical across matching C++ variants/repetitions.

- [`main-observations.csv`](main-observations.csv) retains every observation.
- [`main-groups.csv`](main-groups.csv) contains min/median/max by seed and workload.
- [`main-provenance.json`](main-provenance.json) links source, build, input and
  original metadata hashes to the curated files and figure-selection rule.

The raw record is `local/evidence/strategy-loop/main-20261116/`. Source archives,
executable, inputs, references and full commands remain unchanged there. The
tracked tables are byte-identical copies of the plotter's complete exports;
curated metadata omits local command paths without rewriting the originals.

The runner waited about four minutes for a full minute of low-load samples.
It entered measurement at load 2.274, then completed the matrix in approximately
32 seconds. **Load subsequently reached and ended at 36.116.** The quiet entry
gate does not establish a quiet or isolated measured interval. AC power remained
stable at all 163 recorded checks. CPU placement and frequency were uncontrolled.
No observation was deleted or replaced. These are descriptive results from the
recorded conditions, not stable production speedup or latency estimates.

All eighteen N/K/seed cells repeated the pilot's median ordering: strategy-first
within history storage, event-first within snapshot storage, and
strategy-first/history lowest across all four candidates. See
[findings](../findings.md) for a numeric example, observed ranges and limits.

The [main replay chart](../figures/03-replay-cost-main.png) retains every sample
and separates seed medians. The [main complete-cost chart](../figures/04-whole-run-main.png)
uses the largest N/smallest K/first seed, a rule set before the main campaign,
and one actual run nearest each median total. All eight totals also appear.

The main source/runner configuration and full correctness gate are separately
recorded; the C++ implementation and executable are unchanged from the pilot.
The main source archive corresponds to the same base revision with recorded
uncommitted implementation changes. Source hashes identify the actual checked
and measured code. The main preflight passed 72 untimed workers and all debug,
sanitizer and release tests.

## Pilot

This is an exploratory synthetic-input pilot completed on 16 November 2026
local time, not the main measurement campaign.

- [`pilot-observations.csv`](pilot-observations.csv): all 192 fresh-process
  observations, with individual stage/complete times, dimensions, seed, repeat,
  order position, byte counts, RSS and checked-output hashes. No samples removed.
- [`pilot-groups.csv`](pilot-groups.csv): descriptive min/median/max per candidate,
  input and K, keeping the two input seeds separate. Four samples per cell.
- [`pilot-provenance.json`](pilot-provenance.json): curated scientific metadata,
  exact original-record/source/binary/input hashes and figure-selection rules.

The raw campaign, source snapshot, executable, input/reference CSVs and command
records are retained privately under
`local/evidence/strategy-loop/pilot-20261116-started/`. The tracked observation
CSV is the plotter's complete table, without changing any numeric values. The
curated provenance omits local command paths; the original metadata is retained
unchanged. The base Git revision had uncommitted implementation changes, so the
saved source archive is necessary to identify the actual executed code.

## Conditions and interpretation

Apple M3, 16 GiB RAM, eight logical CPUs, macOS 15.6.1 arm64, GCC 16.2,
`-O3 -DNDEBUG -std=c++23 -fno-fast-math -ffp-contract=off`. Hardware model and RAM
were read in a follow-up because the sandbox denied the in-run query; that
failure remains in the original manifest.

The declared entry load gate passed at 3.954, with a limit of 4. Load later
reached 12.631 and ended there. AC power was stable at all 50 recorded checks.
There was no CPU affinity, frequency control or process isolation. Treat the
timings as exploratory; four samples per cell and rising load do not establish
a stable production speedup or latency distribution.

The campaign finished in about 9.4 seconds and retained about 14.6 MB of evidence.
Prepared work intervals ranged from 0.316 to 84.281 ms. The timer's minimum
positive consecutive-read delta was 1 microsecond; 9,960 of 10,000 pairs read the
same time. Zero deltas do not imply free timing calls. Maximum observed worker
RSS was 36,913,152 bytes. All accounting checks passed.

At every tested N/K/seed cell, median prepared cost was lower for strategy-first
within history-contiguous storage and lower for event-first within snapshot
storage. Strategy-first/history had the lowest median among all four candidates
at each tested cell. These are observations on this run, not a causal cache or
SIMD explanation. The complete matrix is retained, including variation.

The [replay chart](../figures/03-replay-cost-pilot.png) shows every sample and
separate per-seed medians. The [complete-cost chart](../figures/04-whole-run-pilot.png)
uses the largest N and smallest K to make the preparation cost visible. Each
stack is one actual run nearest its group's median total; all four totals appear
as ticks. This selection is documented in the figure metadata. Stage medians
were not independently spliced into an invented run.

The earlier launch in `pilot-20261116/` was held at the entry gate with zero
workers. It is preserved separately; none of its samples were replaced because
none existed. The [main-campaign plan](../measurement-plan.md) records the
subsequent bounded confirmation run.
