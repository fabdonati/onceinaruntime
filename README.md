# Once in a Runtime

New ideas and performance claims, put to the test.

Start with a claim: an algorithm is faster, an abstraction makes a design simpler, or a new technique changes how we solve a problem. What happens when we try it, and which assumptions change the answer?

Once in a Runtime explores programming ideas through small experiments and explanations. Performance is a recurring question; the subjects can also range across software, numerical methods, systems and language design. The question determines the tools, whether that means C++, Rust, OCaml, Python or something else. Each investigation separates its motivating source, hypotheses, evidence and limitations.

Articles and subscriptions: [Once in a Runtime on Substack](https://onceinaruntime.substack.com).

This repository holds the code and reproduction instructions. The first experiment uses C++20 and has a working correctness and smoke pipeline. There are no published performance findings yet.

## Local setup

Requirements: a C++20 compiler, CMake 3.21 or newer, Make, and Python 3.10 or newer. C++ and the runner need no third-party libraries; chart generation uses Matplotlib in a local virtual environment. The checked presets use Unix Makefiles; other generators can be configured manually in a separate build directory.

```sh
cmake --preset debug
cmake --build --preset debug
./build/debug/toolchain_check
ctest --preset debug

cmake --preset sanitize
cmake --build --preset sanitize
ctest --preset sanitize

cmake --preset release
cmake --build --preset release
```

Sanitizer and debug builds are for correctness. Only optimized builds are suitable for timing. Do not build or run other heavy work during measurement.

## Investigations

1. [Message replay: scanning versus indexing](experiments/001-message-replay/brief.md). Bounded implementation and correctness checks available. [Findings and next step](experiments/001-message-replay/findings.md) record validation status. No published performance conclusions.

## Reproduce the smoke pipeline

After building and testing release, from the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-analysis.txt
python3 tools/capture_environment.py --output build/environment.json
python3 tools/run_replay.py --config experiments/001-message-replay/configs/smoke.json --runs 3 --environment build/environment.json --output build/replay-smoke
.venv/bin/python experiments/001-message-replay/analysis/analyze.py build/replay-smoke --output build/replay-smoke/analysis
```

Use a new output directory for each invocation: the runner refuses to overwrite data. Capturing hardware details may require running outside a restricted shell; failed or empty queries remain recorded. The smoke configuration uses a 6.4 MB input batch, 64 topics and one selected topic, with 48-byte payloads. It checks the pipeline and supports no broad performance conclusion.

The initial local smoke dataset is not included in this repository. Generate your own smoke output with the commands above; inspect the [result format and interpretation limits](experiments/001-message-replay/results/README.md) before reading the chart as evidence. The pinned chart dependencies are in [requirements-analysis-lock.txt](requirements-analysis-lock.txt), recorded with Python 3.14. Use that file in place of requirements-analysis.txt when recreating that analysis environment.

Environment details and exact reproduction commands accompany each experiment. Raw smoke observations must be labelled preliminary. Large future datasets should be retained outside Git with a manifest and content hashes if they outgrow this repository; no external storage is needed yet.

## License

The code is available under the [MIT license](LICENSE).
