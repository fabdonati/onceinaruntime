# Toolchain and reproduction

The measured host was an Apple M3 MacBook Air, 16 GB RAM, macOS 15.6.1 ARM64,
with GCC 16.2.0/libstdc++, CMake/CTest 4.3.1, Python 3.14.4, NumPy 2.5.4 and
Matplotlib 3.11.2. Native SIMD held two doubles or four floats on that build;
another target can differ. The implementation uses C++20 `<experimental/simd>`.

Install Python requirements as described in the root README. Run from the root:

```sh
cmake --preset debug
cmake --build --preset debug
ctest --preset debug
cmake --preset sanitize
cmake --build --preset sanitize
ctest --preset sanitize
cmake --preset barrier-release
cmake --build --preset barrier-release
ctest --preset barrier-release
.venv/bin/python studies/barrier-options/analysis/verify.py \
  --binary build/barrier-release/bin/barrier_bench --output build/barrier-oracle
```

Debug and sanitizer results check correctness, not performance. All output
directories must be fresh. Ordinary debug/sanitize/release presets include both
precisions; `barrier-*` keeps the original double-only build and `precision-*`
includes the extension. Presets select `g++-16`; a supporting compiler can be
selected explicitly in a fresh build directory.

Release flags include `-O3 -DNDEBUG -std=c++20 -fPIC -fno-fast-math
-ffp-contract=off`, plus warnings. No LTO or forced disabling of auto-vectorization
is added. Each build's `compile_commands.json` records exact commands.

## Original double campaign

The completed main used 100000 paths, 252 dates, seeds 11/29/47, barriers
105/120/150, both layouts, three methods and six balanced orders: 324 prepared
plus 324 complete-valuation observations in sequential fresh processes.
It is complete; reorganization does not require a timing rerun.

For a separately intended reproduction, use the frozen runner:

```sh
.venv/bin/python studies/barrier-options/analysis/run_main.py --check
.venv/bin/python studies/barrier-options/analysis/run_main.py --output build/barrier-main
```

It requires stable AC and starting one-minute load no higher than half the CPU
count, checks again after preparation, records later load and retains inconvenient
observations. Limits are 30 minutes and separate 1-GiB evidence/RSS bounds. A held
or partial attempt is not a completed campaign. The original pilot runner stays
because current runners share its snapshot/reference helpers; pilot-only chart
scripts were retired.

## Figures without new timing

Selected candidates are in `figures/`. Given retained main evidence, regenerate
the schematic and main analysis into new directories:

```sh
MPLCONFIGDIR=build/matplotlib .venv/bin/python \
  studies/barrier-options/analysis/draw_mechanism.py --output build/barrier-mechanism
MPLCONFIGDIR=build/matplotlib .venv/bin/python \
  studies/barrier-options/analysis/main_views.py /path/to/retained-main \
  --output build/barrier-main-figures --mechanism build/barrier-mechanism
```

The generator checks the matrix and input hashes and invokes no pricing worker.
The main directory needs canonical seed-11 factors, reference lifetimes/flags,
`manifest.json` and `observations.json`. Output includes raw rows, matched effects,
descriptive summaries and PNG/SVG figures. The schematic is an invented teaching
workload, not a performance observation.

On the original machine the unchanged main evidence is at
`local/evidence/barrier-options/main-20261114-c`, excluded from Git. Historical
records retain their original paths; the local migration map describes relocation.
Use retained source archives and recorded flags for the exact measured checkout.
Current runner/style paths differ from that checkout.

The [precision guide](precision/README.md) documents its separate prepared pilot.
Synthetic paths and uncontrolled desktop timing do not establish production HFT
latency. See [findings](findings.md) for the increased-load limitation.
