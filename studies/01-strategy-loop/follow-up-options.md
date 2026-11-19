# Follow-up experiments

The [mdspan comparison](mdspan-check.md) found the same address calculations
and memory operations with manual indexing. The
[compiler inspection](mechanism-check.md) also showed how the two traversal
orders handle account state. Three questions remain open.

- **What accounts for the timing difference?** Collect counters for the four
  existing versions on the same QQQ window. Measure replay separately from
  input preparation. Check which cache and branch events the profiler supports
  on the chosen CPU, and report cycles and instructions per account update
  alongside them.
- **How long does a streaming engine take to respond?** Feed it one event at a
  time, with intervals fixed in advance. Compare immediate processing and
  bounded batching using arrival-to-decision latency, queue depth, missed
  deadlines and throughput. The batch replay here assumes the full history
  is already available.
- **How do the chosen settings fare on unseen prices?** Pick the EMA settings
  and fee assumptions using an earlier period. Then freeze them and evaluate
  return, drawdown and turnover on a later period. Vary execution costs in a
  separately labeled sensitivity analysis.
