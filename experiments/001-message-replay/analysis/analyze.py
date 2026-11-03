"""Summarize retained smoke runs and draw a chart; never interpret these as findings."""

import argparse
import csv
import json
import statistics
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    manifest = json.loads((args.results / "manifest.json").read_text())
    if manifest["status"] != "complete":
        parser.error("only complete runs can be summarized")
    runs = sorted(args.results.glob("run-*.json"))
    if len(runs) != manifest["runs_requested"]:
        parser.error("raw run count differs from the manifest")
    rows = []
    for run, path in enumerate(runs):
        data = json.loads(path.read_text())
        if data["parameters"] != manifest["config"]:
            parser.error("mixed configurations")
        for observation in data["observations"]:
            rows.append({"run": run, **observation})
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "observations.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summaries = []
    for algorithm in ("scan", "indexed"):
        durations = [row["query_ns"] / 1000 for row in rows if row["algorithm"] == algorithm]
        summaries.append({"algorithm": algorithm, "queries": len(durations),
                          "median_query_us": statistics.median(durations),
                          "min_query_us": min(durations), "max_query_us": max(durations)})
    with (args.output / "summary.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)

    with plt.rc_context({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False}):
        figure, axis = plt.subplots(figsize=(8, 5.3))
        for position, summary in enumerate(summaries):
            # Each dot is one fresh process's query median; error bar is all observed queries' range.
            medians = [statistics.median([row["query_ns"] / 1000 for row in rows
                                          if row["run"] == run and row["algorithm"] == summary["algorithm"]])
                       for run in range(len(runs))]
            center = summary["median_query_us"]
            axis.errorbar(position, center,
                          yerr=[[center - summary["min_query_us"]], [summary["max_query_us"] - center]],
                          fmt="_", markersize=24, capsize=7, color="#174a7e", linewidth=2)
            offsets = [(i - (len(medians) - 1) / 2) * 0.045 for i in range(len(medians))]
            axis.scatter([position + offset for offset in offsets], medians, s=32, color="#d16b22", zorder=3)
        axis.set_xticks([0, 1], ["Contiguous scan", "Topic index + heap merge"])
        axis.set_xlim(-0.5, 1.5)
        axis.set_ylim(bottom=0)
        axis.set_ylabel("Complete retrieval duration (µs)")
        axis.grid(axis="y", alpha=0.22)
        config = manifest["config"]
        figure.suptitle("PRELIMINARY · measurement pipeline smoke check", fontsize=14, weight="bold")
        axis.set_title(f"{config['messages']:,} records · {config['payload-bytes']} B payload · "
                       f"{config['selected-topics']}/{config['topics']} selected topics", fontsize=11, pad=14)
        note = (f"{len(runs)} processes × {config['repetitions']} query pairs; {config['warmups']} warm-up pairs/process.\n"
                "Bar: pooled median and observed min–max. Dots: process medians.\n"
                "Warm queries include record copying; not per-message latency or a performance conclusion.")
        figure.text(0.08, 0.025, note, fontsize=9, linespacing=1.5)
        figure.tight_layout(rect=(0.025, 0.18, 1, 0.94))
        figure.savefig(args.output / "smoke-query-duration.png", dpi=160)
        figure.savefig(args.output / "smoke-query-duration.svg")
        plt.close(figure)
    (args.output / "analysis-metadata.json").write_text(json.dumps({
        "matplotlib": matplotlib.__version__, "input": str(args.results),
        "interpretation": "preliminary harness check; pooled samples are not independent processes",
        "exclusions": "none"}, indent=2) + "\n")
    print(f"Saved CSV tables and preliminary chart to {args.output}")


if __name__ == "__main__":
    main()
