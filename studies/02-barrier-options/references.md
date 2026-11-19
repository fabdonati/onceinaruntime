# Focused prior-work check

Checked 11 November 2026. These are background references for an independently posed investigation, not newly published source-led recommendations. This is not an exhaustive literature review.

- Lang, Passing, Kipf, Boncz, Neumann and Kemper, [Make the most out of your SIMD investments: counter control flow divergence in compiled query pipelines](https://d-nb.info/1202257798/34), 2019, DOI 10.1007/s00778-019-00547-y. Sections 4–7 describe CPU AVX-512 refill strategies, implementation overhead, workload dependence and selection thresholds. This directly rules out presenting lane refill itself as our invention. Its database workloads and hardware do not establish our two-lane ARM option-pricing result.
- [Intel ISPC Performance Guide](https://ispc.github.io/perfguide.html), living documentation, accessed 11 November 2026. Its gather/scatter and instrumentation sections explain the costs of irregular access and how logical active-lane statistics can be collected separately. This supports inspecting access patterns and keeping instrumentation outside timing; it does not predict which policy wins here.
- NVIDIA's 19 March 2020 GPU option-pricing example remains motivation/background; its existing early termination is not our novelty.

One additional stream-compaction PDF fetch returned HTTP 403 and was not used as evidence. No exact CPU barrier-option implementation match was established by this focused search; absence from this search does not establish novelty.
