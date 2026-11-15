# When an option disappears, what happens to its SIMD lane?

Does replacing finished SIMD lanes save enough time to pay for input access and
bookkeeping? Compare scalar early exit, fixed native groups and lane refill,
with identical ordered outputs and two physical input layouts.

## Current status

The original double implementation, independent correctness checks and bounded
main campaign are complete: 324 observations in each of two timing scopes.
Nearly full logical occupancy did not uniformly improve runtime in this campaign.
Increased desktop load and broad variation limit stronger claims.

The separate float/double extension is implemented and independently checked.
Its timing pilot has not run. Changing precision changes storage, arithmetic
and native pack width together; this is not an isolated lane-count experiment.

The [article](article.md) is a preliminary manuscript with result/caption
placeholders. The [selected figure candidates](figures/README.md) use the latest
retained typography and original evidence. Final selection remains open.

Next: review the figures and bounded claim, then integrate the measured results
into the article. The prepared precision pilot can run separately in a quiet
AC-powered window; reorganization collected no new timings.

## Working files

| Material | Location |
| --- | --- |
| Article manuscript | [article.md](article.md) |
| Model and equal-output contract | [brief.md](brief.md) |
| Observations and limitations | [findings.md](findings.md) |
| Toolchain and commands | [environment.md](environment.md) |
| Supporting prior work | [references.md](references.md) |
| C++ implementation / checks | `src/`, `tests/` |
| Python references, runners and plotting | `analysis/` |
| Frozen workload configurations | `configs/` |
| Float/double extension | [precision/README.md](precision/README.md) |
| Selected figures | [figures/README.md](figures/README.md) |
| Tables and evidence relationship | [results/README.md](results/README.md) |

Run commands from the repository root. This study uses C++20 with the Parallelism
TS in `std::experimental`, rather than the standard C++26 `<simd>` interface.
