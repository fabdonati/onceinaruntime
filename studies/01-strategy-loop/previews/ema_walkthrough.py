"""Render a checked, untimed EMA walkthrough from the retained synthetic input."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'studies/01-strategy-loop/analysis'))
from reference import features, account
from plot import style, PALETTE
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'local/evidence/strategy-loop/main-20261116/n32768-s11.csv'
    with source.open() as stream:
        bars = [(int(r['timestamp']), float(r['open']), float(r['close']))
                for r in csv.DictReader(stream)]
    # Fixed editorial choice: the first 256 eligible bars, using 10/30 spans.
    # Keep the study's common 96-bar warm-up; do not restart the EMAs at the crop.
    first, last = 96, 351
    matrix = features(bars, [10, 30])
    targets = [row[0] > row[1] for row in matrix]
    full, _ = account(bars, targets, first, diagnose=False)
    with (ROOT / 'studies/01-strategy-loop/figures/accounts.csv').open() as stream:
        expected = next(r for r in csv.DictReader(stream)
                        if (int(r['fast']), int(r['slow'])) == (10, 30))
    for key, value in full.items():
        assert math.isclose(value, float(expected[key]), rel_tol=2e-12, abs_tol=1e-9), key
    # One extra bar keeps the displayed last bar free of forced liquidation.
    _, trace = account(bars[:last + 2], targets[:last + 2], first)
    trace = trace[:-1]
    assert len(trace) == 256 and trace[-1]['bar'] == last
    for row in trace:
        assert row['target_long'] == int(targets[row['bar'] - 1])
        assert row['liquidation_fee'] == 0
    x = np.arange(first, last + 1)
    equity = np.array([r['equity'] for r in trace])
    marks = np.r_[1000., equity]
    peaks = np.maximum.accumulate(marks)
    dd = 1 - marks / peaks
    trough = int(np.argmax(dd))
    peak = int(np.argmax(marks[:trough + 1]))
    mark_x = np.r_[first - 1, x]
    trades = sum(r['opening_event'] != 0 for r in trace)
    serif = style()
    fig = plt.figure(figsize=(12, 10))
    grid = fig.add_gridspec(3, 1, height_ratios=[3.1, .55, 2.7],
                           left=.10, right=.95, bottom=.16, top=.76, hspace=.33)
    ax = fig.add_subplot(grid[0])
    strip = fig.add_subplot(grid[1], sharex=ax)
    wealth = fig.add_subplot(grid[2], sharex=ax)
    fig.text(.07, .955, 'Two averages. One little account.', fontfamily=serif, fontsize=29)
    fig.text(.07, .915, 'Follow a 10 / 30 EMA pair from price, to decision, to account value.', fontsize=13)
    fig.text(.07, .875, 'CHECKED SYNTHETIC EXAMPLE  /  First 256 eligible bars · seed 11 · fees included',
             fontsize=10, color=PALETTE['muted'])
    fig.text(.10, .805, '01   Watch the two averages', fontfamily=serif, fontsize=18)
    ax.plot(x, [bars[t][2] for t in x], color=PALETTE['muted'], alpha=.65, lw=1, label='Closing price')
    ax.plot(x, [matrix[t][0] for t in x], color=PALETTE['blue'], lw=2.1, label='Fast EMA · 10 bars')
    ax.plot(x, [matrix[t][1] for t in x], color=PALETTE['red'], lw=2.1, label='Slow EMA · 30 bars')
    ax.legend(loc='upper left', ncol=3, frameon=False, fontsize=10)
    ax.set_ylabel('Price')
    ax.margins(y=.25)
    for event, marker, label in [(1, '^', 'Buy'), (-1, 'v', 'Sell')]:
        rows = [r for r in trace if r['opening_event'] == event]
        ax.scatter([r['bar'] for r in rows], [bars[r['bar']][1] for r in rows],
                   marker=marker, s=40, color=PALETTE['ink'], zorder=5)
    buy = next(r['bar'] for r in trace if r['opening_event'] == 1)
    ax.annotate('Buy at the next open', xy=(buy, bars[buy][1]),
                xytext=(buy + 15, min(bars[t][2] for t in x) - .15),
                fontsize=10, arrowprops=dict(arrowstyle='->', color=PALETTE['ink']),
                bbox=dict(facecolor=PALETTE['paper'], edgecolor='none', pad=2))
    strip.set_title('02   Hold stock when the previous close says fast > slow',
                    fontfamily=serif, fontsize=16, loc='left', pad=12)
    holding = np.array([r['shares_after_open'] > 0 for r in trace])
    strip.bar(x, 1, width=1, color=[PALETTE['blue'] if h else PALETTE['panel'] for h in holding],
              edgecolor='none', align='center')
    strip.set_ylim(0, 1)
    strip.set_yticks([])
    strip.text(1, -.4, 'Blue = holding stock   ·   Paper = cash   ·   ▲ buy / ▼ sell at opening prices',
               transform=strip.transAxes, ha='right', fontsize=9, color=PALETTE['baseline'])
    wealth.set_title('03   Follow the money', fontfamily=serif, fontsize=18, loc='left', pad=12)
    wealth.plot(mark_x, marks, color=PALETTE['blue'], lw=2.2)
    wealth.axhline(1000, lw=.8, ls='--', color=PALETTE['muted'])
    wealth.fill_between(mark_x[peak:trough + 1], marks[peak:trough + 1], marks[peak],
                        color=PALETTE['red'], alpha=.13)
    wealth.scatter([mark_x[peak], mark_x[trough]], [marks[peak], marks[trough]],
                    color=PALETTE['red'], s=25, zorder=4)
    wealth.annotate(f'Largest fall from a peak: {100*dd[trough]:.1f}%',
                    xy=(mark_x[trough], marks[trough]), xytext=(.40, .87),
                    textcoords='axes fraction', fontsize=10,
                    arrowprops=dict(arrowstyle='->', color=PALETTE['red']),
                    bbox=dict(facecolor=PALETTE['paper'], edgecolor='none', pad=3))
    wealth.set_ylabel('Account value')
    wealth.set_xlabel('Synthetic bar number · same timeline in all three panels', labelpad=10)
    wealth.margins(y=.25)
    wealth.set_xlim(first - 1, last + 1)
    for a in (ax, strip):
        a.tick_params(axis='x', bottom=False, labelbottom=False)
    for a in (ax, wealth):
        a.grid(axis='y', color=PALETTE['rule'], alpha=.35, lw=.6)
    fig.text(.10, .085, f'1,000 to {equity[-1]:,.2f}', fontfamily=serif, fontsize=19)
    fig.text(.43, .085, f'{100*dd[trough]:.1f}% largest drawdown', fontfamily=serif, fontsize=17)
    fig.text(.77, .085, f'{trades} buy / sell events', fontfamily=serif, fontsize=17)
    fig.text(.10, .058, 'Values describe this displayed interval. Ending value includes any open holding; no sale is forced at the crop.', fontsize=9)
    fig.text(.07, .022, 'ONCE IN A RUNTIME   /   INVENTED PRICES · UNTIMED WALKTHROUGH · NOT A MARKET BACKTEST',
             fontsize=9, color=PALETTE['baseline'])
    for ext in ('png', 'svg'):
        fig.savefig(args.output / f'ema-walkthrough.{ext}', dpi=180)
    plt.close(fig)
    with (args.output / 'trace.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=trace[0].keys())
        writer.writeheader()
        writer.writerows(trace)
    metadata = dict(kind='untimed illustration; actual checked synthetic outputs',
                    selection='10/30 pair; first 256 eligible bars, fixed before inspection',
                    first=first, last=last, common_warmup=96, capital=1000, fee=.0001,
                    ending_equity=float(equity[-1]), maximum_drawdown=float(dd[trough]), trades=trades,
                    full_period_summary_check='passed against retained C++ accounts.csv',
                    input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (args.output / 'provenance.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    main()
