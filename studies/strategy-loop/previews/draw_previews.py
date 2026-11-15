"""Draw editorial design mockups. No experiment or benchmark is performed."""

from pathlib import Path
import argparse
import json
import os

HERE = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(HERE / ".mpl-cache"))
os.environ.setdefault("XDG_CACHE_HOME", str(HERE / ".cache"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.patches import Rectangle, FancyArrowPatch
import numpy as np


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, required=True)
OUTPUT = parser.parse_args().output.resolve()
OUTPUT.mkdir(parents=True, exist_ok=False)
FIGURES = OUTPUT / "figures"
FIGURES.mkdir()
STYLE_PATH = HERE.parents[2] / "publication" / "visual-style.json"
STYLE = json.loads(STYLE_PATH.read_text())
P = STYLE["palette"]
HEAD = font_manager.FontProperties(family=["Georgia", "DejaVu Serif"])
BODY = font_manager.FontProperties(family=["Arial", "DejaVu Sans"])
plt.rcParams.update({
    "font.family": ["Arial", "DejaVu Sans"], "font.size": 12,
    "text.color": P["ink"], "axes.labelcolor": P["ink"],
    "xtick.color": P["muted"], "ytick.color": P["muted"],
    "axes.edgecolor": P["rule"], "axes.facecolor": P["paper"],
    "figure.facecolor": P["paper"], "savefig.facecolor": P["paper"],
    "svg.fonttype": "path",
})

MOCK = {
    "status": "FICTIONAL VALUES / NOT BENCHMARK RESULTS",
    "purpose": "Chart layout review only; shapes are not predictions.",
    "measured_observations": 0,
    "config_counts": [8, 16, 32, 64, 128, 256, 512, 1024],
    "fictional_replay_ns_per_strategy_bar": {
        "history_contiguous": {
            "strategy_first": [3.5, 3.4, 3.5, 3.6, 3.8, 4.3, 5.1, 6.3],
            "event_first": [5.2, 4.9, 4.6, 4.4, 4.2, 4.0, 4.1, 4.4],
        },
        "snapshot_contiguous": {
            "strategy_first": [4.2, 4.5, 4.9, 5.3, 5.9, 6.5, 7.0, 7.4],
            "event_first": [3.9, 3.8, 3.8, 3.9, 4.1, 4.8, 5.9, 7.1],
        },
    },
    "fictional_whole_run_ms": [
        {"label": "History / strategy-first", "order": "strategy", "prepare": 110, "setup": 9, "replay": 130, "summary": 7},
        {"label": "History / event-first", "order": "event", "prepare": 110, "setup": 9, "replay": 94, "summary": 7},
        {"label": "Snapshot / strategy-first", "order": "strategy", "prepare": 134, "setup": 9, "replay": 148, "summary": 7},
        {"label": "Snapshot / event-first", "order": "event", "prepare": 134, "setup": 9, "replay": 112, "summary": 7},
    ],
    "heatmap": {
        "status": "FICTIONAL RETURN SURFACE / NOT A BACKTEST",
        "formula": "0.12*sin(fast_index*0.65)+0.10*cos(slow_index*0.58)-0.075; mask fast>=slow",
        "scale_labels": ["loss", "flat", "gain"],
    },
}
(OUTPUT / "mock-data.json").write_text(json.dumps(MOCK, indent=2) + "\n")


def text(fig, x, y, value, size=12, color=None, head=False, **kwargs):
    return fig.text(x, y, value, fontsize=size, color=color or P["ink"],
                    fontproperties=HEAD if head else BODY, **kwargs)


def card(number, title, subtitle, fictional=True):
    fig = plt.figure(figsize=(13, 9.4), dpi=140)
    text(fig, .055, .948, f"ONCE IN A RUNTIME    /    FIGURE {number}", 10, P["muted"])
    text(fig, .055, .878, title, 27, head=True)
    text(fig, .055, .832, subtitle, 12, P["baseline"])
    warning = "FICTIONAL VALUES / NOT BENCHMARK RESULTS" if fictional else "SCHEMATIC / LOGICAL OPERATIONS, NOT ELAPSED TIME"
    fig.add_artist(Rectangle((.055, .761), .89, .037, transform=fig.transFigure,
                             facecolor=P["panel"], edgecolor="none"))
    text(fig, .066, .774, warning, 10, P["red"], weight="bold")
    fig.add_artist(plt.Line2D([.055, .945], [.104, .104], transform=fig.transFigure,
                             color=P["rule"], lw=.8))
    return fig


def save(fig, name):
    fig.savefig(FIGURES / f"{name}.png", dpi=140)
    fig.savefig(FIGURES / f"{name}.svg")
    plt.close(fig)


def minimal(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(length=0, pad=8)


# Figure 1: an invented financial surface establishes the workload, not an edge.
fig = card(1, "A thousand versions of one rule",
           "Opening: what are we asking the computer to calculate?")
ax = fig.add_axes([.12, .205, .50, .50])
n = 12
fast, slow = np.meshgrid(np.arange(n), np.arange(n))
values = .12 * np.sin(fast * .65) + .10 * np.cos(slow * .58) - .075
surface = np.ma.masked_where(fast >= slow, values)
cmap = LinearSegmentedColormap.from_list("paper_return", [P["red"], P["paper"], P["blue"]])
cmap.set_bad(P["panel"])
ax.imshow(surface, origin="lower", cmap=cmap,
          norm=TwoSlopeNorm(vmin=-.28, vcenter=0, vmax=.28), interpolation="nearest")
for k in np.arange(-.5, n, 1):
    ax.axhline(k, color=P["paper"], lw=1.1)
    ax.axvline(k, color=P["paper"], lw=1.1)
ticks = [0, 3, 6, 9, 11]
labels = ["8", "24", "64", "160", "320"]
ax.set_xticks(ticks, labels)
ax.set_yticks(ticks, labels)
ax.set_xlabel("Fast EMA span (bars)", labelpad=10)
ax.set_ylabel("Slow EMA span (bars)", labelpad=10)
for spine in ax.spines.values():
    spine.set_visible(False)
ax.tick_params(length=0)
ax.text(7.8, 2.0, "fast ≥ slow\nnot tested", ha="center", va="center", color=P["muted"], fontsize=12)
legend = fig.add_axes([.69, .30, .025, .32])
gradient = np.linspace(-.28, .28, 256).reshape(-1, 1)
legend.imshow(gradient, origin="lower", aspect="auto", cmap=cmap,
              norm=TwoSlopeNorm(vmin=-.28, vcenter=0, vmax=.28))
legend.set_xticks([])
legend.set_yticks([0, 127, 255], ["loss", "flat", "gain"])
legend.yaxis.tick_right()
legend.tick_params(length=0, pad=8)
for spine in legend.spines.values():
    spine.set_visible(False)
text(fig, .69, .657, "Net period return", 12)
text(fig, .69, .225, "One tile = one parameter pair.\nEvery replay must reproduce\nthe same decisions and results.", 12, P["baseline"], linespacing=1.5, va="top")
text(fig, .055, .064, "Design only: fictional surface; no market data or strategy was simulated.", 10, P["muted"])
save(fig, "01-parameter-landscape")


# Figure 2: precise schematic of independent state trajectories and separate storage.
fig = card(2, "Two ways through the same work",
           "After the rule: change visit order while preserving each strategy’s chronology.", False)


def traversal(rect, column_first, color, title):
    ax = fig.add_axes(rect)
    rows, cols = 4, 5
    for row in range(rows):
        for col in range(cols):
            ax.add_patch(Rectangle((col, row), .91, .83, facecolor=P["panel"], edgecolor=P["paper"]))
    seq = [(col + .455, row + .415) for col in range(cols) for row in range(rows)] if column_first else [(col + .455, row + .415) for row in range(rows) for col in range(cols)]
    for i, (start, end) in enumerate(zip(seq, seq[1:])):
        jump = (i + 1) % (rows if column_first else cols) == 0
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=12,
                                    color=color, lw=1.6 if not jump else 1.0,
                                    alpha=.95 if not jump else .32,
                                    linestyle="-" if not jump else ":", zorder=2))
    for i, (x, y) in enumerate(seq[:4]):
        ax.plot(x, y, "o", color=color, markersize=18, zorder=3)
        ax.text(x, y, str(i+1), color="white", ha="center", va="center", fontsize=10, zorder=4)
    ax.set_xlim(-.15, cols + .1)
    ax.set_ylim(rows + .1, -.18)
    ax.set_xticks(np.arange(cols) + .455, ["A", "B", "C", "D", "E"])
    ax.xaxis.tick_top()
    ax.set_yticks(np.arange(rows) + .415, ["t0", "t1", "t2", "t3"])
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title(title, loc="left", fontsize=14, pad=28, color=color)


traversal([.10, .395, .36, .28], True, P["blue"], "Strategy-first  ·  down a column")
traversal([.56, .395, .36, .28], False, P["red"], "Event-first  ·  across a row")
text(fig, .10, .361, "Columns = strategies     Rows = market events", 11, P["baseline"])
text(fig, .10, .318, "A separate choice: how the EMA feature table is stored", 16, head=True)

for y, label, cells in [
    (.237, "History together", ["w0,t0", "w0,t1", "w0,t2", "w1,t0", "w1,t1", "w1,t2"]),
    (.172, "Snapshot together", ["w0,t0", "w1,t0", "w0,t1", "w1,t1", "w0,t2", "w1,t2"]),
]:
    text(fig, .10, y+.011, label, 11)
    for i, label_cell in enumerate(cells):
        x = .31 + i * .095
        fig.add_artist(Rectangle((x, y), .09, .04, transform=fig.transFigure,
                                 facecolor=P["panel"], edgecolor=P["rule"], lw=.6))
        text(fig, x+.045, y+.012, label_cell, 11, ha="center")
text(fig, .055, .064, "The update grid is event × strategy; the feature table is event × EMA window (w).", 10, P["muted"])
save(fig, "02-traversal-and-layout")


# Figure 3: imagined observations illustrate the intended visual form only.
fig = card(3, "What does one strategy-bar cost?",
           "Results section: compare traversal orders within each physical layout.")
k = np.asarray(MOCK["config_counts"])
for panel, (key, title) in enumerate([
    ("history_contiguous", "Contiguous indicator histories"),
    ("snapshot_contiguous", "Contiguous event snapshots"),
]):
    ax = fig.add_axes([.105 + panel*.46, .305, .35, .355])
    for order, color, marker, label in [
        ("strategy_first", P["blue"], "o", "Strategy-first"),
        ("event_first", P["red"], "s", "Event-first"),
    ]:
        center = np.asarray(MOCK["fictional_replay_ns_per_strategy_bar"][key][order])
        for offset in [-.18, -.06, .08, .19]:
            ax.scatter(k, center + offset, s=12, color=color, alpha=.24, edgecolor="none")
        ax.plot(k, center, marker=marker, color=color, lw=2, markersize=5, label=label)
    ax.set_xscale("log", base=2)
    ax.set_xlim(7, 1170)
    ax.set_ylim(0, 8.5)
    ax.set_xticks([8, 32, 128, 512, 1024], ["8", "32", "128", "512", "1,024"])
    ax.set_xlabel("Parameter pairs tested (K)", labelpad=11)
    if panel == 0:
        ax.set_ylabel("Replay ns / strategy-bar  ·  lower is better", labelpad=12)
    ax.set_title(title, loc="left", fontsize=13, pad=14)
    ax.grid(axis="y", color=P["rule"], lw=.6, alpha=.55)
    minimal(ax)
    ax.legend(loc="upper left", frameon=False, fontsize=10)
text(fig, .105, .185, "Hold history length and feature population fixed. Show individual process samples.\nA crossover, a consistent ordering, or an unresolved difference are all possible outcomes.", 11, P["baseline"], linespacing=1.5, va="top")
text(fig, .055, .064, "The dots, curves and crossover above are invented design inputs; none are predicted findings.", 10, P["muted"])
save(fig, "03-replay-cost")


# Figure 4: stages from fictional complete runs, never mixed stage medians.
fig = card(4, "The replay is only part of the bill",
           "Optional near the conclusion: does preparation change the practical choice?")
ax = fig.add_axes([.29, .265, .64, .39])
rows = MOCK["fictional_whole_run_ms"]
for i, row in enumerate(rows):
    y = len(rows)-1-i
    left = 0
    for stage in ["prepare", "setup", "replay", "summary"]:
        color = {"prepare": "#B8A493", "setup": "#DDCBB9", "summary": "#3F3F3F",
                 "replay": P["blue"] if row["order"] == "strategy" else P["red"]}[stage]
        width = row[stage]
        ax.barh(y, width, left=left, height=.57, color=color, edgecolor=P["paper"], lw=1)
        if stage in ["prepare", "replay"]:
            ax.text(left + width/2, y, str(width), ha="center", va="center",
                    color="white" if stage == "replay" else P["ink"], fontsize=11)
        left += width
    ax.text(left + 5, y, f"{left} ms", va="center", fontsize=12)
ax.set_yticks(range(len(rows)), [row["label"] for row in reversed(rows)], fontsize=11)
ax.set_xlim(0, 345)
ax.set_xlabel("Complete-run elapsed time (ms)", labelpad=10)
ax.grid(axis="x", color=P["rule"], lw=.6, alpha=.4)
ax.set_axisbelow(True)
minimal(ax)
for x, color, label in [(.10, "#B8A493", "Features / layout"), (.34, "#DDCBB9", "State setup"),
                        (.54, P["blue"], "Replay (blue / red)"), (.79, "#3F3F3F", "Summary")]:
    fig.add_artist(Rectangle((x, .188), .014, .018, transform=fig.transFigure, facecolor=color, edgecolor="none"))
    text(fig, x+.022, .189, label, 10)
text(fig, .10, .133, "Keep this figure only if complete-run cost changes the decision; otherwise use a small table.", 11, P["baseline"])
text(fig, .055, .064, "Illustrative complete-run components only. Final totals must come from retained real runs.", 10, P["muted"])
save(fig, "04-whole-run-cost")


# A contact sheet lets the reader review the figure sequence together.
fig = plt.figure(figsize=(16, 13.8), dpi=140)
text(fig, .035, .965, "One market, a thousand strategies", 28, head=True)
text(fig, .035, .934, "Article storyboard  /  three main figures + one optional cost breakdown", 13, P["baseline"])
text(fig, .035, .907, "DESIGN MOCKUPS · FICTIONAL VALUES · NOT BENCHMARK RESULTS", 11, P["red"], weight="bold")
names = ["01-parameter-landscape", "02-traversal-and-layout", "03-replay-cost", "04-whole-run-cost"]
for i, name in enumerate(names):
    col, row = i % 2, i // 2
    ax = fig.add_axes([.022 + .49*col, .48 - .43*row, .475, .41])
    ax.imshow(plt.imread(FIGURES / f"{name}.png"))
    ax.axis("off")
fig.savefig(FIGURES / "storyboard.png", dpi=140)
plt.close(fig)

print(json.dumps({"figures": str(FIGURES), "result_previews": 3, "schematics": 1,
                  "measured_observations": 0, "font": HEAD.get_file()}))
