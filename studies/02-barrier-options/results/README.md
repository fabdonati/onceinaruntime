# Results and evidence

The CSVs here are unchanged compact tables from the retained 14 November main
analysis. All 324 prepared observations and their 324 complete-valuation partners
appear in `observations.csv`; other tables retain matched effects, per-seed
summaries, chronological diagnostics and phase means. They describe the double
study, not the unrun precision pilot.

[Selected figures](../figures/README.md) are separate from raw evidence. Three
input seeds with six process repetitions are not eighteen independent workload
populations. Ranges are descriptive, not confidence intervals or tails. Phase
means from the same complete intervals add to the mean total. Logical lane
occupancy is not hardware utilization.

Raw binary inputs, references, stdout/stderr, individual observations, manifests,
frozen source archives and checks remain excluded from Git. On the original
machine they are under `local/evidence/barrier-options/`. Main: `main-20261114-c`;
pilot: `pilot-20261111`; precision checks: `precision-verification-20261114`.
Original manifests and hashes were not rewritten during relocation.

The local `local/migration/path-map.json` records old/new paths, and
`local/migration/evidence-before.json` records all retained evidence hashes.
The verified retired-code/planning archive is separate. Neither collection is
an off-machine backup.

The study moved from `experiments/003-barrier-simd/`. Pricing C++ files retain
their original bytes. Runner paths, build setup, docs and figure paths changed;
use the retained `source.zip` and flags to reconstruct the measured checkout.
A fresh reproduction from current source needs its own provenance.

Historical source snapshots may contain old workflow metadata and stay private.
Commands are in [../environment.md](../environment.md).
