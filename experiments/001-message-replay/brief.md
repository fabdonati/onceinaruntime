# 001: When does indexing a message stream beat scanning it?

Status: bounded implementation available. See findings.md for executed checks and readiness. No performance conclusions yet.

## Source and evidence

Nicholas Yang, [Scaling and benchmarking a critical message bus using a new indexing strategy](https://blog.janestreet.com/scaling-and-benchmarking-a-critical-message-bus/), Jane Street, 5 October 2026. Reopened 1 November 2026.

| Category | Claim or assumption | Evidence and implication |
| --- | --- | --- |
| Source, explicit | Linear filtering was cache friendly but became costly as recovery demand grew. | “Filtering messages was overloading our servers”. This motivates testing selection density. |
| Source, explicit | Aria indexes topic partitions and reconstructs order with a heap merge. | Same section. Our flat topic IDs omit hierarchical subscriptions and partition filtering. |
| Source, explicit | Heap implementation affected indexed recovery performance. | “Prototyping and benchmarking the index”. Merge work must remain inside our timing boundary. |
| Source qualification | The introduction associates a CPU reduction with production workloads; the closing section describes preliminary staging results. | “How did the optimizations do?”. Treat this as reported evidence under unspecified conditions, not a portable speedup. |
| Assessment | The article is a useful mechanism study, not a reproduction specification. | Hardware, compiler flags, full datasets and run distributions are not supplied. |

Read the filtering and prototyping sections carefully; skim disk splitting for this experiment. This project tests an inspired mechanism, not Aria. No source benchmark values are targets.

## Question and hypotheses

A reader requests a sequence range and selected integer topics from a finite immutable message batch. Does avoiding irrelevant records outweigh binary searches, heap operations, index memory and construction?

Hypotheses, all unmeasured at planning time:

- Sparse selection may favour indexing.
- Dense selection or many selected topics may favour contiguous scanning.
- Index construction may require many reads to amortize.

## Smallest useful design

- C++20, no library dependencies. Sequence numbers equal zero-based positions. Ranges are half open `[begin, end)`, clipped to the batch; reversed ranges are rejected. Unknown topics are ignored and repeated selections are deduplicated.
- One contiguous byte store, with a 16-byte header followed by configurable fixed-size payloads. Headers use `memcpy` so arbitrary strides do not create unaligned accesses or object lifetime violations.
- Scan: traverse only the requested range and test a precomputed topic bitmap in constant time.
- Index: build sorted position lists per topic in batch, then binary search the range and merge subscribed lists with a min-heap. Count and account for vector capacity, including empty topic lists.
- Both paths copy identical full records into an output buffer reserved before measurement. Selection normalization is also outside timing for both. Heap construction and heap allocation are inside indexed retrieval timing.
- No live ingestion, eviction, ring store, concurrency, disk, networking or hierarchical topics. Uniform topics and a skew model (80% forced to topic zero, 20% uniform over all topics) are synthetic, not market traffic.

Validate explicit expected records and boundaries, then randomized differential cases with recorded seeds. Run debug and ASan/UBSan before timing. Hash and compare outputs outside timed intervals to consume results and catch divergence.

## Measurement plan and stopping point

First use three fresh-process smoke runs, eight query pairs per run and two warm-up pairs. Alternate which algorithm runs first. Retain every query duration in nanoseconds, record visits, returned messages, common stream construction, batch index construction and capacity-based memory. Stream construction includes synthetic generation; it is not a production ingestion benchmark. Index memory excludes allocator bookkeeping and process RSS.

Time complete warm retrieval operations, including output copying and heap work. These are query durations, not per-message latency. Validation between queries perturbs caches; no cold-cache claim is supported. Timer calibration, configuration, commands, environment, compiler flags and Git state accompany raw results. Smoke charts summarize function only, with median and observed range; no tail percentile claims.

After smoke validation, vary selection count, topic count, batch size and payload size in a small matrix. Include a dataset substantially above the 16 MiB performance-cluster L2, but do not assert cache residency from size alone. Add skew only to resolve a question. Do not run a full campaign before inspecting stability, timing scale, memory limits and background load on the intended measurement machine.

Stop this initial phase when a clean local checkout builds and tests, documented smoke commands run, retained data regenerate a chart, and limitations and the next step are recorded. No numerical conclusion or post is required at this stage.
