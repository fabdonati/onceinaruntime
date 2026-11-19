"""Alternative editorial maps of retained, checked synthetic account summaries."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'studies/01-strategy-loop/analysis'))
from plot import style, PALETTE
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm, Normalize
from matplotlib.ticker import PercentFormatter
import matplotlib.tri as tri
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'studies/01-strategy-loop/figures/accounts.csv'
    with source.open() as stream:
        rows = list(csv.DictReader(stream))
    fast, slow, ret, dd = [np.array([float(r[k]) for r in rows])
                           for k in ('fast', 'slow', 'net_return', 'max_drawdown')]
    ret, dd = 100 * ret, 100 * dd
    assert len(rows) == 1128 and len(set(zip(fast, slow))) == 1128
    assert np.all(fast < slow) and np.isfinite(ret).all() and np.isfinite(dd).all()
    serif = style()
    norm = TwoSlopeNorm(vmin=-60, vcenter=0, vmax=140)
    # Keep zero neutral and use a wider light-to-dark blue range for gains.
    # Fixed return levels retain their numeric meaning; no quantile remapping.
    color_stops = [(-60, PALETTE['red']), (-40, '#D74B3F'), (-20, '#EDAA91'),
                   (0, PALETTE['paper']), (20, '#DDEBF3'), (40, '#B8D6E7'),
                   (60, '#7CB4D4'), (80, '#388BBE'), (100, '#0865A3'),
                   (120, PALETTE['blue']), (140, '#082746')]
    cmap = LinearSegmentedColormap.from_list('paper-return',
             [(float(norm(value)), color) for value, color in color_stops])
    assert ret.min() >= -60 and ret.max() <= 140
    common = '1,128 EMA pairs · 32,768 synthetic bars · seed 11 · same fees and warm-up'

    def header(fig, title, subtitle):
        fig.text(.07, .95, title, fontfamily=serif, fontsize=29)
        fig.text(.07, .905, subtitle, fontsize=12)
        fig.text(.07, .87, common, fontsize=10, color=PALETTE['muted'])

    def export(fig, name):
        for ext in ('png', 'svg'):
            fig.savefig(args.output / f'{name}.{ext}', dpi=180)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 9))
    fig.subplots_adjust(left=.11, right=.84, top=.80, bottom=.18)
    mesh = tri.Triangulation(fast, slow)
    levels = np.arange(-60, 141, 10)
    art = ax.tricontourf(mesh, ret, levels=levels, cmap=cmap, norm=norm)
    for level in (0, 30, 60, 90, 120):
        ink = '#FFFFFF' if level >= 90 else PALETTE['ink']
        lines = ax.tricontour(mesh, ret, levels=[level], colors=ink,
                             linewidths=.8 if level == 0 else .6, alpha=.8)
        ax.clabel(lines, inline=True, fontsize=9, fmt=lambda v: f'{v:.0f}%')
    ax.scatter(fast, slow, s=1.2, color=PALETTE['paper'], alpha=.16, linewidths=0)
    ax.plot([2, 94], [4, 96], color=PALETTE['rule'], lw=.8)
    ax.set(xlim=(0, 98), ylim=(0, 98), xlabel='Fast EMA span · bars', ylabel='Slow EMA span · bars')
    ax.set_xticks([2, 20, 40, 60, 80, 96])
    ax.set_yticks([2, 20, 40, 60, 80, 96])
    ax.set_aspect('equal')
    ax.text(53, 37, 'Read it like a map', fontfamily=serif, fontsize=20)
    ax.text(53, 24, 'Each point is one tested pair.\nContour labels show equal returns.\nBlue = gain; red = loss.', fontsize=11, linespacing=1.65)
    ax.text(53, 9, 'Blank region: fast ≥ slow\nThese pairs are excluded.', fontsize=10, color=PALETTE['muted'])
    bar = fig.colorbar(art, ax=ax, fraction=.04, pad=.045, shrink=.78, spacing='proportional',
                      ticks=[-60, -30, 0, 30, 60, 90, 120, 140])
    bar.ax.yaxis.set_major_formatter(PercentFormatter(xmax=100, decimals=0))
    bar.set_label('Net return over the synthetic period', labelpad=10)
    header(fig, 'A landscape of EMA settings', 'The same results, drawn as a topographic map.')
    fig.text(.07, .105, 'Contours linearly interpolate between tested pairs; they are not additional simulations.', fontsize=10)
    fig.text(.07, .073, 'The shape belongs to this invented price path. It does not establish profitable or robust settings.', fontsize=10)
    fig.text(.07, .03, 'ONCE IN A RUNTIME   /   CHECKED SYNTHETIC OUTPUTS · DESIGN PREVIEW', fontsize=9, color=PALETTE['baseline'])
    export(fig, '01-ema-contours')

    fig, ax = plt.subplots(figsize=(11, 9))
    fig.subplots_adjust(left=.12, right=.83, top=.79, bottom=.20)
    point_cmap = LinearSegmentedColormap.from_list('span', ['#B4C9D7', PALETTE['blue']])
    art = ax.scatter(dd, ret, c=slow, cmap=point_cmap, norm=Normalize(4, 96),
                     s=22, alpha=.75, linewidths=.25, edgecolors=PALETTE['paper'])
    ax.axhline(0, color=PALETTE['red'], lw=1)
    ax.text(57, 3, 'Break even after fees', color=PALETTE['red'], fontsize=9, ha='right')
    ax.set(xlim=(0, 60), ylim=(-65, 150),
           xlabel='Largest fall from an account peak · maximum drawdown',
           ylabel='Net return over the synthetic period')
    ax.xaxis.set_major_formatter(PercentFormatter(100, decimals=0))
    ax.yaxis.set_major_formatter(PercentFormatter(100, decimals=0))
    ax.grid(color=PALETTE['rule'], alpha=.3, lw=.6)
    ax.set_axisbelow(True)
    # Label predetermined pairs, not ex-post winners.
    for pair, location in [((2, 4), (37, -35)), ((10, 30), (30, 65)), ((32, 96), (25, 128))]:
        index = np.flatnonzero((fast == pair[0]) & (slow == pair[1]))[0]
        ax.scatter(dd[index], ret[index], facecolors='none', edgecolors=PALETTE['ink'], s=95, lw=1, zorder=5)
        ax.annotate(f'{pair[0]} / {pair[1]} EMA\n{return_label(ret[index])}, {dd[index]:.1f}% drawdown',
                    xy=(dd[index], ret[index]), xytext=location, fontsize=10,
                    arrowprops=dict(arrowstyle='-', color=PALETTE['ink'], lw=.8),
                    bbox=dict(facecolor=PALETTE['paper'], edgecolor='none', pad=3))
    bar = fig.colorbar(art, ax=ax, fraction=.04, pad=.045, shrink=.78, ticks=[4, 20, 40, 60, 80, 96])
    bar.set_label('Slow EMA span · bars', labelpad=10)
    header(fig, 'A return comes with a drawdown', 'Each dot is one EMA pair. Higher means more return; left means a smaller fall.')
    fig.text(.07, .12, 'All 1,128 pairs are shown. Labels identify three fixed examples, not selected winners.', fontsize=10)
    fig.text(.07, .085, 'These are outcomes on one invented history, not forecasts or independent market samples.', fontsize=10)
    fig.text(.07, .03, 'ONCE IN A RUNTIME   /   CHECKED SYNTHETIC OUTPUTS · DESIGN PREVIEW', fontsize=9, color=PALETTE['baseline'])
    export(fig, '02-ema-return-drawdown')
    (args.output / 'provenance.json').write_text(json.dumps(dict(
        input='studies/01-strategy-loop/figures/accounts.csv',
        input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        configurations=len(rows), kinds=['linearly interpolated contour map', 'all-pair scatter'],
        contour_color_stops=color_stops, contour_levels=levels.tolist(),
        input_kind='checked synthetic outputs; no new simulation or timing',
        labelled_pairs=[[2, 4], [10, 30], [32, 96]]), indent=2) + '\n')


def return_label(value):
    return f'{value:+.1f}% return'


if __name__ == '__main__':
    main()
