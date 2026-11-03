# 001: Validation status and next step

This file reports functional validation, not an experimental performance conclusion. The initial local smoke dataset is retained separately and is not included in this repository. The public source and smoke configuration let you exercise the pipeline on your own machine.

## Initial setup

The repository contains C++20 CMake presets for debug/release/sanitizers, a toolchain probe, an environment recorder, a bounded replay library, correctness checks, a sequential smoke runner and Matplotlib analysis. Each run records the actual Git revision and working-tree state and retains a source archive with SHA-256 hashes.

The implementation stores complete records contiguously. The baseline tests a topic bitmap; the index stores sorted per-topic positions and merges them with a heap. Both copy the same full records in sequence order. Index construction is timed separately from generation and retrieval. This is batch replay, with no online maintenance or concurrent readers.

## Validation record

- The C++20/libc++ toolchain probe built and ran before replay implementation.
- Debug, optimized and ASan/UBSan builds passed fixed correctness cases and 400 randomized cases (seeds 1, 42, 20261101, 16429347).
- Checks cover exact payload bytes and sequence order, empty/full/duplicate/unknown selections, range boundaries and clipping, zero payloads, unaligned records, both topic distributions, deterministic generation and invalid range/storage sizes.
- Local smoke runs exercised output validation, observation retention and chart generation. Those checks establish harness function only; no numerical performance finding or chart is published here.
- The initial local calibration reported a zero-nanosecond median for back-to-back clock reads. This reflects a limitation of that calibration at the observed timer granularity, not proof of a free timer. Record positive deltas, effective resolution and calibration variation before a full campaign. Calibration is not subtracted from query durations.

## Limits and next step

No conclusion about when indexing wins is supported by the single smoke configuration. Query samples within each process are correlated; the chart's observed range is descriptive, not an uncertainty estimate. Index-memory numbers exclude allocator overhead and the transient heap. The index, reference and output buffers remain resident for both algorithms, which affects working-set interpretation. Output buffers are reserved from the known reference result size, avoiding allocation during retrieval but assuming a capacity estimate an application might not have.

The source's hierarchical subscriptions, dynamic retention and production load are omitted. No counters were collected, so elapsed times cannot establish a cache explanation. Results from this macOS host do not support Linux scheduler claims.

The initial build, correctness and retention pipeline is ready. Full measurement readiness still depends on timer characterization and controlled conditions. Next, choose the intended campaign host and stable power, inspect preliminary durations relative to timer calibration and process variation, and then run a small matrix of selection density, topic count, input size and payload size. Include batches above the reported cluster L2 and reason about all resident buffers. Estimate index amortization from separately measured construction and query costs only after stable measurements. Keep all observations and investigate skew if it changes a specific interpretation. Full measurements and post drafts remain future work.
