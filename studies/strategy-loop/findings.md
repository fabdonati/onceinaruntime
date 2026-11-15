# Strategy-loop findings

## Executed: layout example, 15 November 2026

The existing GCC 16.2/libstdc++ route compiled the actual `std::mdspan` view in
C++23 mode. The compiler reported `__cplusplus=202302` and
`__cpp_lib_mdspan=202207`. Ordinary and ASan/UBSan executions passed.

The example independently checks six logical values, both mappings' strides,
zero/one-element boundaries, and a counterexample where viewing a history-ordered
buffer as snapshot-ordered reads a different value. This establishes the local
API route and illustrates that a mapping change does not rearrange storage.

Exact commands, source hash, revision/dirty state and outputs are retained in
`local/evidence/strategy-loop/preflight-20261115/report.json`, excluded from Git.
The runnable source is [examples/layout.cpp](examples/layout.cpp).

Root debug configure/build/CTest and root sanitizer configure/build/CTest also
passed after integration: five CTest entries each, including the existing barrier
and precision checks, twenty Python analysis tests, and the new layout example.

## Not established

No backtest engine, independent trading oracle, historical dataset, performance
observation, vectorization finding or speedup exists for this study. Charts under
`previews/` are fictional design inputs. The example does not measure mdspan
overhead or demonstrate that either loop order is faster.

## Next step

Implement the accounting contract's smallest deterministic reference and fixtures,
then the four equal-output replay variants. Use [brief.md](brief.md); freeze a
bounded timing plan only after correctness and untimed scale checks pass.
