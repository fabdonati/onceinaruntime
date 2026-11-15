# Once in a Runtime

New ideas and performance claims, put to the test.

Small investigations into performance, low latency and modern C++, with examples
from numerical software, quant finance and trading systems. Each study keeps its
question, implementation, checks, findings, figures and manuscript together.

Articles and subscriptions: [Once in a Runtime](https://onceinaruntime.substack.com).

## Studies

| Study | Working material |
| --- | --- |
| [Barrier options and SIMD](studies/barrier-options/README.md) | Checked C++ implementation, measured main study, article draft and prepared float/double extension. |
| [One market, a thousand strategies](studies/strategy-loop/README.md) | Preliminary article and proposed loop-order/layout experiment. Preview values are fictional; no implementation or timing evidence exists yet. |

Each study's README records its status and next step. Manuscripts on `main` are
work in progress; their presence does not mean an article has been published.
Stable folder names are independent of publication order.

## Build and check

The implemented study uses C++20, CMake 3.21+, Make, Python 3.10+, NumPy and
Matplotlib. Its `<experimental/simd>` interface requires a supporting compiler
and standard library. The checked local route is GCC 16.2/libstdc++.
The proposed strategy study targets C++23 `mdspan`; its exact setup is unverified.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-analysis.txt
cmake --preset debug
cmake --build --preset debug
ctest --preset debug
cmake --preset sanitize
cmake --build --preset sanitize
ctest --preset sanitize
```

Presets select `g++-16` and include both barrier precisions. To use another
supporting compiler in a fresh build directory, override it, for example
`cmake --preset debug -DCMAKE_CXX_COMPILER=g++`. The local Python environment is
used automatically when present; otherwise set `Python3_EXECUTABLE` explicitly.

Only release builds are used for timing. See the
[barrier reproduction guide](studies/barrier-options/environment.md) and
[precision run guide](studies/barrier-options/precision/README.md).
CI checks correctness and analysis, without timing campaigns.

## Publication

- [About](publication/about.md)
- [Publication introduction draft](publication/introduction.md)
- [Subscriber welcome and name story](publication/welcome-email.md)
- [Figure colors and typography](publication/visual-style.json)

The approved About and welcome wording is retained. Updating these files does
not update Substack automatically. Manuscripts contain explicit unresolved
passages where evidence or author review is still needed.

## Evidence and maintenance

Track current source, manuscripts, selected figures and compact numeric tables.
Large raw runs, historical source snapshots, reviews and private research stay
in ignored local storage. [Barrier result documentation](studies/barrier-options/results/README.md)
explains the evidence relationship and reproduction limits.

Retired message-replay and batch-lifecycle studies are outside the active build.
Their source and superseded planning were preserved in one verified local archive
before removal. Historical measurement manifests were not rewritten.

Code is available under the [MIT license](LICENSE).
