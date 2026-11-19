# Float versus double: barrier-path precision extension

14 November 2026. Implementation preparation authorized; no timing campaign has
been run. This is a bounded extension of experiment 003, preserving its original
double pricing sources and all original measurements.

Question: what runtime and numerical differences accompany four native float
lanes instead of two native double lanes on the current ARM build?

Compare scalar early exit, fixed native groups and native refill, with path-major
and step-major inputs. FP64 uses the original `barrier_core`. FP32 uses float
inputs, float stock updates, comparisons and payoff arithmetic. Both reduce
payoffs in ascending path-ID order using double accumulation. FP32 rounds the
contract's discount once. The declared barriers, spot and strike are exact in
both formats. Do not describe this as an isolated test of lane count: precision,
input traffic, pack width and possibly path stopping decisions change together.

Generate canonical FP64 scenarios using the existing generator. Round once to
binary32, then rearrange the same values for the second layout. No independent
float random stream. Test each precision's three methods for exact equality to
an independent date-wise oracle of that precision, including ordered payoffs,
lifetimes and knock-outs. Literal arithmetic and near-barrier counterexamples
audit the references. Agreement with the FP32 oracle is an implementation check,
not proof that FP32 is sufficiently accurate for a financial application.

Record per-seed/barrier numerical differences from FP64: knock-out disagreement
in both directions, stopping-date changes, zero-payoff changes, maximum absolute
payoff error, RMS payoff error, mean signed error, ordered aggregate difference
and the sample variation of the paired payoff differences. Also evaluate an
untimed FP64 oracle on rounded FP32 factors widened back to FP64 to distinguish
input quantisation from the remaining arithmetic/discount rounding changes.
These components can interact through early exits; they are not additive causal
attributions. No universal acceptable error threshold is declared.

The runnable timing pilot uses 8192 paths, 252 dates, seeds 11/29/47, barriers
105/120/150 and six cyclic rotations of the six precision/method candidates per
case. Every candidate occupies every order position once. This is 648 sequential
prepared-input observations. One selected-method warm-up precedes each timed
observation. Input generation/casting/layout, validation, references, diagnostics
and serialization are outside timing; payoff writes and common aggregation are
inside. Input/casting byte counts are retained. No complete-valuation performance
claim is supported by this extension's timing scope.

Require release mode, stable AC and a one-minute start load no higher than half
the available CPU count. Sample power/load throughout, retain later load changes,
and never replace inconvenient observations. Limits: 30 minutes, 1 GiB evidence,
1 GiB conservative parent-plus-child peak RSS. Preserve raw observations,
commands, sources/flags/revision/dirty state, inputs/references and hashes. Stop on
failure, nonfinite values, correctness mismatch, power instability or resource
limits. Run one campaign only; a larger matrix needs a separate decision after
the pilot.

Preparation stops when debug/sanitizer checks, independent verification,
untimed end-to-end smoke and the result-analysis checks pass, with runnable
commands documented. Main timing and final plots remain pending a quiet window.
