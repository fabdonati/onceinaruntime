# Toolchain and reproduction

The measured host was an Apple M3 MacBook Air, 16 GB RAM, macOS 15.6.1 ARM64,
with GCC 16.2.0/libstdc++, CMake/CTest 4.3.1, Python 3.14.4, NumPy 2.5.4 and
Matplotlib 3.11.2. Native SIMD held two doubles or four floats on that build;
another target can differ. The implementation uses C++20 `<experimental/simd>`.

Install the Python packages listed in the [root README](../../README.md).
Run the following commands from the repository root.

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
.venv/bin/python studies/02-barrier-options/analysis/verify.py \
  --binary build/barrier-release/bin/barrier_bench --output build/barrier-oracle
```

The first six commands build and test the debug and sanitizer versions.
`barrier-release` builds the double-precision pricer used for timing. The
`verify.py` command compares its path results with the Python reference. Use
a fresh output directory for each run. The default presets include both
precisions, while the `barrier-*` presets build only the original double study.
The presets select `g++-16`. Choose another compiler in a fresh build directory.

Release flags include `-O3 -DNDEBUG -std=c++20 -fPIC -fno-fast-math
-ffp-contract=off`, plus warnings. No LTO or forced disabling of auto-vectorization
is added. Each build's `compile_commands.json` records exact commands.

## Original double campaign

The completed main used 100000 paths, 252 dates, seeds 11/29/47, barriers
105/120/150, both layouts, three methods and six balanced orders: 324 prepared
plus 324 complete-valuation observations in sequential fresh processes.
Use `--check` to inspect the build and host conditions before starting a new
run. Then give the benchmark an unused output directory.

```sh
.venv/bin/python studies/02-barrier-options/analysis/run_main.py --check
.venv/bin/python studies/02-barrier-options/analysis/run_main.py --output build/barrier-main
```

The runner requires stable AC and a starting one-minute load no higher than
half the CPU count. It checks again after preparing the inputs and records
the load throughout the run. The limits are 30 minutes, 1 GiB of evidence and
1 GiB of observed combined peak RSS. It keeps all timings collected before a
failure or resource limit.

## Figures without new timing

The article's figures are in [figures/](figures/README.md). To regenerate them
from a saved main run, first render the two-lane example:

```sh
MPLCONFIGDIR=build/matplotlib .venv/bin/python \
  studies/02-barrier-options/analysis/draw_mechanism.py --output build/barrier-mechanism
MPLCONFIGDIR=build/matplotlib .venv/bin/python \
  studies/02-barrier-options/analysis/main_views.py /path/to/retained-main \
  --output build/barrier-main-figures --mechanism build/barrier-mechanism
```

The generator checks the matrix and input hashes and invokes no pricing worker.
The main directory needs canonical seed-11 factors, reference lifetimes/flags,
`manifest.json` and `observations.json`. Output includes raw rows, matched effects,
descriptive summaries and PNG/SVG figures. The schematic is an invented teaching
workload, not a performance observation.

The original campaign is stored locally under
`local/evidence/barrier-options/main-20261114-c`. Its source archive and
`compile_commands.json` describe the exact build. The figures and tables in
this repository come from that campaign.

The [precision guide](precision/README.md) documents its separate prepared pilot.
Synthetic paths and uncontrolled desktop timing do not establish production HFT
latency. See [findings](findings.md) for the increased-load limitation.
