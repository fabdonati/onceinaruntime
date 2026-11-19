# Once in a Runtime

Experiments in C++ performance, numerical software and trading systems.
Each study includes an article, the code and instructions for running it.

[Once in a Runtime on Substack](https://onceinaruntime.substack.com)

## Articles

| No. | Article draft | Code and reproduction |
| --- | --- | --- |
| 01 | [One market, a thousand strategies](studies/01-strategy-loop/article.md) | [Strategy replay](studies/01-strategy-loop/README.md) · [Run guide](studies/01-strategy-loop/benchmark.md) · [Results](studies/01-strategy-loop/results/README.md) |
| 02 | [When an option disappears, what happens to its SIMD lane?](studies/02-barrier-options/article.md) | [Barrier options](studies/02-barrier-options/README.md) · [Run guide](studies/02-barrier-options/environment.md) · [Results](studies/02-barrier-options/results/README.md) |

## Build and test

Run these commands from the repository root. Use CMake 3.21 or newer, Make,
Python 3.10 or newer, and a compiler with the required library features. The
presets use GCC 16 and libstdc++. Study 01 needs C++23 `std::mdspan`. Study 02
uses C++20 and `<experimental/simd>`.

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

To select a different compiler, pass `-DCMAKE_CXX_COMPILER=...` when configuring
a fresh build. Set `-DOIR_STRATEGY_EXAMPLES=OFF` to build only the barrier study
on a compiler that lacks `mdspan`. CMake uses `.venv/bin/python` when available.
You can also set `Python3_EXECUTABLE` explicitly.

The debug and sanitizer presets check correctness. Use the release builds and
the linked run guides for timing. CI runs the correctness checks.

## Publication

[About](publication/about.md) · [Introduction draft](publication/introduction.md)
· [Subscriber welcome](publication/welcome-email.md)

The repository includes individual timings, derived tables and figures. Raw
market prices and full campaign archives are stored separately. See each study's
results for workload details and measurement limits.

Code is available under the [MIT license](LICENSE).
