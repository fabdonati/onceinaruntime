# Main measurement plan after the pilot

The historical extension has its own [completed protocol](historical-plan.md)
and `configs/historical-{pilot,main}.json`. The text below records the original
synthetic campaign; its observations are never pooled with historical timings.

Protocol variation, 17 November: following explicit author authorization, a
separate reproduction used `--allow-battery` and temporary local evidence output.
The frozen workload matrix and counts were unchanged. The runner records power
policy and actual power samples; AC remains its default. This battery campaign
completed all 576 observations with low recorded load. Keep it separately
identified from the original AC plan below; see findings for the comparison.

Status: frozen before execution and completed, 16 November 2026. All 576
observations passed output checks. The quiet entry gate passed after about four
minutes, but load rose during measurement; see `findings.md` for interpretation.
The pilot and original observations remain separate. The main matrix is
`configs/main.json`. The following records the plan chosen before the main run.

The pilot establishes a useful duration scale and a layout-dependent traversal
ordering. Its shortest prepared interval was 0.316 ms versus a 1 microsecond
minimum positive timer delta. Four observations per cell were enough to exercise
the harness and expose a candidate pattern; rising host load limits the strength
of the performance conclusion.

## Bounded confirmation run

Keep the existing accounting, generator, input lengths, feature population and
three K values. Add one predeclared seed, 47, and use eight fresh observations
per candidate/cell: two complete balanced-order cycles. That makes
2 N × 3 seeds × 3 K × 4 candidates × 8 repetitions = **576 observations**.
This increases replication and input coverage while keeping the question fixed.
It does not establish behavior across actual market regimes.

Retain a 15-minute run cap, 30-second worker timeout, 512 MiB worker-RSS stopping
limit, 256 MiB evidence cap and 1 GiB free disk reserve. Use one complete matrix,
no resampling slow cases, and retain all failure records. Keep all summary checks
and individual stage times. Recheck the full independent summaries for the added
seed before timing; no diagnostic trace belongs in a timed worker.

Require AC power and a quiet entry interval. Wait at most ten minutes for a full
minute of samples, taken every fifteen seconds, all at or below the existing
load limit of 4. Keep recording load and power throughout the run. The wait is
inside the fifteen-minute total cap. If the interval never arrives, retain a
`not_started` manifest without launching measurement workers. If load
rises again, retain the observations and report the run's limitations; do not
delete individual samples according to their durations. No system setting or
unrelated process needs changing.

A 192-worker pilot took about 9.4 seconds here, including per-worker checks and
metadata collection. The proposed timing matrix would likely take tens of
seconds, but independent-reference generation, builds and checks add time.
Reserve a few quiet minutes rather than treating that pilot scaling estimate as
a promised duration. Background variation remains uncontrolled.

## Dataset and scope

The confirmation run keeps the synthetic performance question and account
illustration. If an observed market
example is desired, choose its instrument, bar interval, price/adjustment
convention and source before introducing it; do not relabel the existing data.

The main campaign has its own configuration, manifest kind, paths and figure
labels. The runner validates the two frozen matrices separately. Existing pilot
manifests and gates are unchanged. Use the main commands in `benchmark.md`.
No additional SIMD, state-layout, threading or strategy variation is needed for
this first comparison.

The final article can claim only the ordering and variation that a valid main
run supports. Cache behavior remains a hypothesis without separate evidence.
The compiler report describes loop vectorization, not a measured reason for the
timing differences. Keep the complete-cost view if its preparation cost continues
to change the practical interpretation at small K.
