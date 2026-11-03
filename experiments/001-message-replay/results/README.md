# Result format

The initial local smoke dataset is retained separately and is not part of this repository. No numerical performance result is published. Use the smoke commands in the root README to generate a complete local example under `build/replay-smoke`.

Each successful campaign directory contains a manifest, build flags, generated compiler commands, a source archive and one JSON file per fresh process. Each process records its own stream/index construction duration and capacity estimates, plus all measured query observations. No successful samples are excluded. Failed invocations are marked failed, not silently merged with successful data. Source hashes describe the files at execution time; later documentation updates can differ from that archived snapshot.

`messages_examined` counts visited records in the original store. It excludes binary-search probes and heap comparisons, so it is not total algorithmic work. Memory is based on C++ object sizes and vector capacities, excluding allocator overhead, executable pages and RSS. The reference and two output buffers are reported separately. Selection storage and transient heap memory are not included in the index capacity estimate.

The analysis emits pooled observations, a CSV with median and observed range, PNG/SVG charts, and its Matplotlib version. The range is not a confidence interval; dots identify individual process medians. Repeated queries within a process are correlated. Regeneration uses only retained JSON; it does not rerun C++.
