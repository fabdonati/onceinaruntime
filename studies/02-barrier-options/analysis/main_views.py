"""Descriptive main-campaign figures. Never runs or replaces a timing observation."""
import argparse
from collections import Counter
import csv
import datetime as dt
import hashlib
import itertools
import json
import math
from pathlib import Path
import platform
import shutil
import statistics as stats
import subprocess
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
METHODS = ('scalar', 'fixed', 'refill')
BARRIERS = (105, 120, 150)
SEEDS = (11, 29, 47)
PHASES = ('generation_ns', 'layout_ns', 'output_allocation_bridge_compute_ns')
MEAN_KEYS = dict(zip((*PHASES, 'complete_ns'),
                     ('generation_mean_ms', 'layout_mean_ms', 'valuation_mean_ms', 'complete_mean_ms')))
PAPER, PANEL, INK = '#FCE9D7', '#F0DECD', '#0F0F0F'
BLUE, RED, GRAY, RULE = '#003C7F', '#BF0000', '#3F3F3F', '#C1B3A5'
GEN, LAYOUT = '#C7AF98', '#766657'
COLORS = dict(zip(METHODS, (GRAY, BLUE, RED)))
LABELS = dict(zip(METHODS, ('Scalar', 'Fixed SIMD', 'Refill SIMD')))
STYLE_PATH = ROOT / 'publication/visual-style.json'
STYLE = json.loads(STYLE_PATH.read_text())
HEAD = fm.FontProperties(family=['Georgia', 'DejaVu Serif'], weight='normal', style='normal')
BODY = fm.FontProperties(family=['Arial', 'DejaVu Sans'])
MARKERS = dict(zip(SEEDS, ('o', 's', '^')))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def summary(values):
    values = list(values)
    if not values or not all(math.isfinite(x) for x in values):
        raise ValueError('empty or nonfinite observations')
    return dict(count=len(values), median=stats.median(values), minimum=min(values), maximum=max(values), mean=stats.mean(values))


def mean_phases(rows):
    for r in rows:
        if sum(r[k] for k in PHASES) != r['complete_ns']:
            raise ValueError('complete interval differs from phase sum')
    values = {MEAN_KEYS[k]: stats.mean(r[k] for r in rows) / 1e6 for k in (*PHASES, 'complete_ns')}
    if not math.isclose(sum(values[MEAN_KEYS[k]] for k in PHASES), values['complete_mean_ms'], abs_tol=1e-10):
        raise ValueError('mean stack is not additive')
    return values


def survival_counts(life, hit, steps):
    life, hit = np.asarray(life), np.asarray(hit)
    if len(life) != len(hit) or np.any(life > steps) or np.any(life < 0) or np.any((hit != 0) & (hit != 1)):
        raise ValueError('invalid lifetime or knockout data')
    counts = len(life) - np.cumsum(np.bincount(life[hit == 1].astype(int), minlength=steps+1))
    if any(counts[d] != np.count_nonzero((hit == 0) | (life > d)) for d in (0, 1, steps//2, steps-1, steps)):
        raise ValueError('survivor boundary count mismatch')
    return counts


def pooled_work(rows, barrier, method):
    unique = []
    for seed in SEEDS:
        chosen = [r for r in rows if (r['seed'], r['barrier'], r['method']) == (seed, barrier, method)]
        values = {(r['useful_lane_steps'], r['available_lane_steps'], r['replacements']) for r in chosen}
        if len(values) != 1:
            raise ValueError('logical work changed across repeats/layouts')
        unique.append(next(iter(values)))
    useful, available, replacements = (sum(r[k] for r in unique) for k in range(3))
    return dict(useful=useful, available=available, replacements=replacements, occupancy=useful/available)


def matched_effect(numerator, denominator):
    return 100 * (numerator / denominator - 1)


def write_csv(path, rows):
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)


def clean(ax):
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0, pad=6)
    ax.set_axisbelow(True)


def save(fig, out, name):
    # Avoid tight cropping: margins and annotation positions are part of the layout.
    for ext in ('png', 'svg'):
        fig.savefig(out / f'{name}.{ext}', dpi=180, facecolor=PAPER)
    plt.close(fig)


def figure_header(fig, title, subtitle, tag='MAIN CAMPAIGN · DESCRIPTIVE RESULTS'):
    fig.text(.06, .967, 'ONCE IN A RUNTIME', fontsize=11, weight='bold', color=BLUE)
    fig.text(.94, .967, tag, ha='right', fontsize=9, color=GRAY)
    fig.text(.06, .905, title, fontproperties=HEAD, fontsize=28)
    fig.text(.06, .861, subtitle, fontsize=12, color=GRAY)


def time_card(fig, bounds, rows, barrier, layout, label_size=11):
    x, y, w, h = bounds
    chosen = [r for r in rows if (r['barrier'], r['layout']) == (barrier, layout)]
    index = {(r['seed'], r['repeat'], r['method']): r for r in chosen}
    ax = fig.add_axes((x, y, w, h))
    ax.set_xlim(-.63, 1.63); ax.set_ylim(0, 60)
    for si, seed in enumerate(SEEDS):
        for repeat in range(6):
            fixed, refill = (index[seed, repeat, m]['prepared_ns']/1e6 for m in ('fixed', 'refill'))
            shift = (repeat-2.5)*.026 + (si-1)*.035
            ax.plot([shift, 1+shift], [fixed, refill], color=GRAY, alpha=.11, lw=.8, zorder=1)
            for xpos, value, method in ((shift, fixed, 'fixed'), (1+shift, refill, 'refill')):
                ax.scatter(xpos, value, s=23, marker=MARKERS[seed], color=COLORS[method], alpha=.58, edgecolor=PAPER, linewidth=.4, zorder=3)
    medians = {m: stats.median(r['prepared_ns']/1e6 for r in chosen if r['method']==m) for m in METHODS}
    ax.axhline(medians['scalar'], ls=(0, (3, 4)), lw=.9, color=GRAY, alpha=.55, zorder=0)
    ax.plot([0, 1], [medians['fixed'], medians['refill']], color=INK, lw=2.5, zorder=4)
    for xpos, method, side in ((0, 'fixed', 'right'), (1, 'refill', 'left')):
        value = medians[method]
        ax.scatter(xpos, value, s=88, color=COLORS[method], edgecolor=PAPER, linewidth=1.8, zorder=5)
        tx = xpos-.16 if method=='fixed' else xpos+.16
        ax.text(tx, value+1.8, f'{value:.2f}', ha=side, va='bottom', fontsize=label_size+2, weight='bold', color=COLORS[method])
    ax.set_xticks((0, 1), ('Fixed SIMD', 'Refill SIMD'))
    for text, method in zip(ax.get_xticklabels(), ('fixed', 'refill')):
        text.set_color(COLORS[method]); text.set_weight('bold')
    ax.set_yticks((0, 20, 40, 60))
    ax.tick_params(labelsize=label_size-1)
    ax.set_ylabel('Milliseconds', fontsize=label_size-1)
    ax.grid(axis='y', color=RULE, alpha=.38)
    clean(ax)
    ax.set_title(('Path-major' if layout=='path' else 'Step-major') + f"  ·  scalar median {medians['scalar']:.2f} ms", fontsize=label_size, loc='left', pad=11)
    if barrier==150 and layout=='step':
        fixed_times=[r['prepared_ns'] for r in chosen if r['method']=='fixed']
        refill_times=[r['prepared_ns'] for r in chosen if r['method']=='refill']
        if min(refill_times)>max(fixed_times):
            ax.text(.5,7.5,'Here, all refill runs took longer\nthan all fixed-group runs.',ha='center',va='center',fontsize=label_size-1,color=GRAY)
    return medians


def comparison_figure(rows, diagnostics, out):
    fig = plt.figure(figsize=(13, 13.3))
    figure_header(fig, 'Full lanes. Mixed results.', 'Refill keeps the slots busy. Does it also finish the same work sooner?')
    fig.text(.06, .821, '100,000 paths × 252 dates · Apple M3 · two double lanes · lower time is faster', fontsize=10, weight='bold')
    for bi, barrier in enumerate(BARRIERS):
        top = .754 - bi*.213
        diag = next(d for d in diagnostics if d['barrier']==barrier)
        fig.add_artist(Line2D([.06,.94],[top+.025,top+.025],transform=fig.transFigure,color=RULE,lw=.8))
        fig.text(.06, top, f'Barrier {barrier}', fontproperties=HEAD, fontsize=18)
        fig.text(.23, top+.001, f"{diag['mean_dates']:.0f} / 252 dates processed per path, on average", fontsize=10, color=GRAY)
        fixed, refill = (diag[m]['occupancy']*100 for m in ('fixed', 'refill'))
        fig.text(.94, top+.001, f'Useful lane slots: fixed {fixed:.1f}%  →  refill >99.99%', fontsize=10, color=BLUE, ha='right')
        for layout, x in (('path', .105), ('step', .565)):
            time_card(fig, (x, top-.168, .35, .124), rows, barrier, layout)
    legend = [Line2D([0],[0],marker=MARKERS[s],color=GRAY,lw=0,label=f'Seed {s}',markersize=5) for s in SEEDS]
    legend += [Line2D([0],[0],color=INK,lw=2.5,marker='o',label='Connected medians',markersize=5), Line2D([0],[0],color=GRAY,lw=.9,ls='--',label='Scalar median')]
    fig.legend(handles=legend, loc='lower left', bbox_to_anchor=(.05,.089), ncol=5, frameon=False, fontsize=9)
    fig.text(.06,.081,'READ IT: each faint line joins the same seed and repeat; thick lines join the two pooled medians.',fontsize=10,weight='bold')
    fig.text(.06,.058,'18 observations per method/case (3 seeds × 6 processes). Matching preserves inputs; separate processes can share system drift.',fontsize=9)
    fig.text(.06,.036,'All fixed/refill observations are shown. Scalar ranges, including a 163.41 ms observation, are in the accompanying full table.',fontsize=9)
    fig.text(.06,.014,'Prepared scope: calculation, payoff writes and ordered aggregation. Generation excluded. Desktop load rose; no confidence intervals or causal claims.',fontsize=8.7)
    save(fig, out, '03-lanes-and-time')
    # Reading-size crops preserve the same data and scale, for narrow article layouts.
    for barrier in BARRIERS:
        fig = plt.figure(figsize=(8.7, 9.8))
        figure_header(fig, f'Barrier {barrier}: follow the clock.', 'Blue = fixed groups. Red = refill. Lower means less elapsed time.', tag='PREPARED INPUT · 18 RUNS PER METHOD')
        diag = next(d for d in diagnostics if d['barrier']==barrier)
        fig.text(.06,.805,f"Useful lane slots: {diag['fixed']['occupancy']*100:.1f}% fixed → >99.99% refill",fontsize=13,weight='bold',color=BLUE)
        time_card(fig,(.15,.493,.68,.235),rows,barrier,'path',13)
        time_card(fig,(.15,.152,.68,.235),rows,barrier,'step',13)
        fig.text(.06,.070,'Dots: 18 runs per method. Thick line: pooled medians. Dashed: scalar median.',fontsize=9.5)
        fig.text(.06,.045,'Faint lines match seed/repeat across separate processes. System load was uncontrolled.',fontsize=9.5)
        fig.text(.06,.020,'100,000 paths × 252 dates · 3 seeds × 6 repeats · see full table for scalar ranges.',fontsize=9.5)
        save(fig,out,f'03-barrier-{barrier}')


def waffle(ax, shares, colors):
    # Each square is one percent of mean total; partial squares preserve exact shares.
    cumulative = np.cumsum([0, *shares])*100
    assert math.isclose(cumulative[-1],100,abs_tol=1e-10)
    for unit in range(100):
        col, row = unit % 10, 9-unit//10
        for phase, color in enumerate(colors):
            start, end = max(unit,cumulative[phase]), min(unit+1,cumulative[phase+1])
            if end > start:
                ax.add_patch(Rectangle((col+(start-unit)*.86, row), (end-start)*.86, .86, facecolor=color, edgecolor='none'))
    ax.set_xlim(-.05,10.05); ax.set_ylim(-.05,10.05); ax.set_aspect('equal'); ax.axis('off')


def cost_figure(rows,out):
    costs=[]
    for layout,method in itertools.product(('path','step'),METHODS):
        selected=[r['complete'] for r in rows if (r['layout'],r['method'])==(layout,method)]
        assert len(selected)==54
        phases=mean_phases(selected)
        costs.append(dict(layout=layout,method=method,observations=54,**phases))
    fig=plt.figure(figsize=(12.4,11.8))
    figure_header(fig,'Most of the bill comes first.','Generate the paths. Arrange their memory. Then calculate the payoffs.')
    fig.text(.06,.815,'Each square = 1% of mean complete-valuation time. Partial squares retain the exact split.',fontsize=10)
    for li,layout in enumerate(('path','step')):
        top=.753-li*.318
        fig.text(.06,top,('Path-major: use the generated order' if layout=='path' else 'Step-major: also transpose the input'),fontproperties=HEAD,fontsize=18)
        for mi,method in enumerate(METHODS):
            x=.06+mi*.307
            c=next(c for c in costs if (c['layout'],c['method'])==(layout,method))
            total=c['complete_mean_ms']
            fig.text(x,top-.040,LABELS[method],fontsize=12,weight='bold',color=COLORS[method])
            fig.text(x,top-.088,f'{total:.1f} ms',fontproperties=BODY,fontsize=23,color=COLORS[method])
            ax=fig.add_axes((x,top-.244,.125,.14))
            waffle(ax,[c[MEAN_KEYS[k]]/total for k in PHASES],(GEN,LAYOUT,COLORS[method]))
            for pi,(label,key,color) in enumerate((('Generate','generation_ns',GRAY),('Layout','layout_ns',LAYOUT),('Price*','output_allocation_bridge_compute_ns',COLORS[method]))):
                yy=top-.134-pi*.042
                fig.text(x+.141,yy,label,fontsize=10,color=color)
                duration=c[MEAN_KEYS[key]]
                value = '<0.1 ms · <0.1%' if 0 < duration < .1 and 0 < 100*duration/total < .1 else f'{duration:.1f} ms · {100*duration/total:.1f}%'
                fig.text(x+.141,yy-.018,value,fontsize=10,weight='bold',color=color)
    fig.text(.06,.107,'54 complete observations per card: all 3 barriers × 3 seeds × 6 repeats, equally weighted.',fontsize=10,weight='bold')
    fig.text(.06,.080,'Arithmetic means of phases from the same complete intervals. Each card adds to its mean total; rounding can differ by 0.1 ms.',fontsize=9)
    fig.text(.06,.055,'*Price includes output allocation, the Python/C++ call, path calculation and ordered aggregation. It is not the separately timed prepared kernel.',fontsize=9)
    fig.text(.06,.030,'Imports, validation, serialization and destruction excluded. NumPy generation + C++ pricing on Apple M3; system load varied.',fontsize=9)
    save(fig,out,'04-whole-valuation')
    return costs


def stock_figure(run,manifest,out):
    factors=np.memmap(run/'seed-11-path.f64',dtype='<f8',mode='r',shape=(100000,252))
    life=np.fromfile(run/'ref-11-120.lifetimes.u64',dtype='<u8')
    hit=np.fromfile(run/'ref-11-120.knocked.u8',dtype='u1')
    payoff=np.fromfile(run/'ref-11-120.payoffs.f64',dtype='<f8')
    example=[]
    fig=plt.figure(figsize=(10.2,6.6))
    figure_header(fig,'One future can stop early.','Six simulated stock paths. Touch 120, and that path contributes zero payoff.',tag='ILLUSTRATION · RETAINED SCENARIOS')
    ax=fig.add_axes((.09,.235,.78,.53))
    for path in range(6):
        price=100.;values=[price];knocked=False
        for date,multiplier in enumerate(factors[path],1):
            price*=float(multiplier);values.append(price)
            if price>=120:
                knocked=True;break
        assert date==life[path] and knocked==bool(hit[path])
        expected=0. if knocked else math.exp(-.02)*max(price-100,0.)
        assert expected==payoff[path]
        color=GRAY if knocked else BLUE
        ax.plot(range(len(values)),values,color=color,lw=1.8 if knocked else 1.3,alpha=.8,ls='-' if path%2==0 else '--')
        if knocked:
            ax.scatter(date,price,color=RED,s=45,zorder=5,edgecolor=PAPER)
            ax.annotate(f'Day {date}: stop this path',xy=(date,price),xytext=(date-105,127),fontsize=11,color=RED,
                        arrowprops=dict(arrowstyle='->',color=RED,lw=1.2))
        example.append(dict(path_id=path,monitoring_dates=list(range(len(values))),prices=values,knocked_out=knocked,lifetime=int(life[path]),payoff=float(payoff[path])))
    ax.axhline(120,color=RED,lw=1.1,ls=(0,(4,3)))
    ax.text(255,120,'Barrier\n120',color=RED,va='center',fontsize=11,weight='bold')
    ax.axhline(100,color=RULE,lw=.7)
    ax.text(255,100,'Starts\nat 100',color=GRAY,va='center',fontsize=10)
    ax.set_xlim(0,252);ax.set_ylim(68,132)
    ax.set_xticks((0,63,126,189,252));ax.set_xlabel('Monitoring date · one simulated year',fontsize=11,labelpad=8)
    ax.set_yticks((80,100,120));ax.set_ylabel('Simulated stock price',fontsize=11)
    ax.grid(axis='y',color=RULE,alpha=.25);clean(ax)
    fig.text(.06,.125,'After the red stop, there is no reason to calculate the rest of that path for this payoff.',fontsize=11,weight='bold')
    fig.text(.06,.075,'First six path IDs, seed 11, barrier 120. Blue paths reach maturity; that alone does not guarantee a positive payoff.',fontsize=9)
    fig.text(.06,.035,'Synthetic risk-neutral pricing scenarios, not forecasts. Colours here describe path outcomes, not execution methods.',fontsize=9)
    save(fig,out,'01-stock-paths')
    (out/'stock-example.json').write_text(json.dumps(example,indent=2)+'\n')
    return example


def diagnostic_figure(rows,manifest,out):
    fig=plt.figure(figsize=(13.5,9))
    figure_header(fig,'Keep the inconvenient observations.','Every timing stays in the record, including the slowest scalar observation.',tag='SUPPORTING DIAGNOSTIC · ALL OBSERVATIONS')
    axes=[fig.add_axes((.10,y,.83,h)) for y,h in ((.57,.20),(.31,.19),(.12,.12))]
    elapsed=[];complete_elapsed=[]
    start=dt.datetime.fromisoformat(manifest['frozen_before_observations_utc'])
    workers={e['id']:e for e in manifest['executions']}
    chronology=[]
    for i,r in enumerate(rows):
        minute=(dt.datetime.fromisoformat(workers[r['id']+'-prepared']['started_utc'])-start).total_seconds()/60
        complete_minute=(dt.datetime.fromisoformat(workers[r['id']+'-complete']['started_utc'])-start).total_seconds()/60
        elapsed.append(minute)
        complete_elapsed.append(complete_minute)
        chronology.append(dict(order=i+1,id=r['id'],seed=r['seed'],barrier=r['barrier'],layout=r['layout'],method=r['method'],prepared_worker_elapsed_minutes=minute,complete_worker_elapsed_minutes=complete_minute,prepared_ms=r['prepared_ns']/1e6,complete_ms=r['complete']['complete_ns']/1e6))
    for method in METHODS:
        selected=[(i,r) for i,r in enumerate(rows) if r['method']==method]
        for scope,ax in (('prepared',axes[0]),('complete',axes[1])):
            y=[r['prepared_ns']/1e6 if scope=='prepared' else r['complete']['complete_ns']/1e6 for i,r in selected]
            x = elapsed if scope=='prepared' else complete_elapsed
            ax.scatter([x[i] for i,r in selected],y,s=16,color=COLORS[method],alpha=.7,label=LABELS[method])
    axes[0].set_yscale('log',base=2);axes[0].set_yticks((10,20,40,80,160),('10','20','40','80','160'))
    axes[0].set_ylim(10,190);axes[0].set_ylabel('Prepared ms\n(log scale)',fontsize=11)
    worst=max(range(len(rows)),key=lambda i:rows[i]['prepared_ns'])
    axes[0].annotate(f"{rows[worst]['prepared_ns']/1e6:.2f} ms · retained",xy=(elapsed[worst],rows[worst]['prepared_ns']/1e6),xytext=(elapsed[worst]+.6,130),fontsize=10,arrowprops=dict(arrowstyle='->',color=GRAY))
    axes[1].set_ylim(250,820);axes[1].set_yticks((300,500,700));axes[1].set_ylabel('Complete ms',fontsize=11)
    samples=[]
    for record in manifest['environment']:
        minute=(dt.datetime.fromisoformat(record['utc'])-start).total_seconds()/60
        if minute>=0:samples.append((minute,record['load_average'][0]))
    axes[2].plot(*zip(*samples),color=GRAY,lw=1.5)
    axes[2].axhline(4,color=RULE,lw=1,ls='--')
    axes[2].text(.1,4.5,'4.0 was the entry gate; later load was retained',fontsize=9,color=GRAY)
    axes[2].set_ylabel('1-min load',fontsize=11);axes[2].set_xlabel('Worker start · minutes since entry to observations',fontsize=11)
    for ax in axes:
        ax.set_xlim(-.05,max(elapsed)+.1);ax.grid(axis='y',color=RULE,alpha=.3);clean(ax)
    axes[0].legend(frameon=False,ncol=3,loc='upper right',fontsize=10)
    for seed in (29,47):
        i=next(i for i,r in enumerate(rows) if r['seed']==seed)
        for ax in axes:ax.axvline(elapsed[i],color=RULE,lw=.9)
        axes[0].text(elapsed[i]+.06,175,f'Seed {seed}',fontsize=9)
    fig.text(.06,.045,'Workloads change over time, so this is a diagnostic, not a causal plot of load versus latency. Power sampled as AC charging throughout.',fontsize=9.5)
    save(fig,out,'05-run-diagnostic')
    write_csv(out/'chronology.csv',chronology)
    return chronology


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--mechanism',type=Path,required=True)
    a=parser.parse_args();run=a.run.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    plt.rcParams.update({'font.family':BODY.get_family(),'font.size':12,'text.color':INK,'axes.labelcolor':INK,
                         'xtick.color':INK,'ytick.color':INK,'figure.facecolor':PAPER,'axes.facecolor':PAPER,'svg.fonttype':'path'})
    manifest=json.loads((run/'manifest.json').read_text());rows=json.loads((run/'observations.json').read_text())
    if manifest['status']!='complete' or len(rows)!=324 or manifest['pricing_processes']!=648:
        raise ValueError('requires the completed 324-pair main campaign')
    expected=set(itertools.product(SEEDS,BARRIERS,('path','step'),range(6),METHODS))
    keys=[(r['seed'],r['barrier'],r['layout'],r['repeat'],r['method']) for r in rows]
    assert len(set(keys))==324 and set(keys)==expected
    inputs={run/'manifest.json',run/'observations.json',run/'execution-plan.json',run/'source.zip',STYLE_PATH}
    inputs.add(run/'seed-11-path.f64')
    for ref in manifest['references']:
        inputs.update(run/meta['name'] for meta in ref['files'].values())
    for ext in ('png','svg','json'):
        name='simd-mechanism-explained-data.json' if ext=='json' else 'simd-mechanism-explained.'+ext
        inputs.add(a.mechanism/name)
    input_hashes={str(p):digest(p) for p in inputs}
    for ref in manifest['references']:
        for meta in ref['files'].values():assert input_hashes[str(run/meta['name'])]==meta['sha256']
    assert input_hashes[str(run/'seed-11-path.f64')]==manifest['datasets'][0]['canonical']['sha256']
    index=dict(zip(keys,rows));flat=[];effects=[]
    for r in rows:
        assert (r['paths'],r['steps'],r['native_width'])==(100000,252,2)
        assert r['timed'] and r['validated_cpp'] and r['complete']['validated'] and r['prepared_ns']>0
        assert sum(r['complete'][k] for k in PHASES)==r['complete']['complete_ns']
        scalar=index[r['seed'],r['barrier'],r['layout'],r['repeat'],'scalar']
        fixed=index[r['seed'],r['barrier'],r['layout'],r['repeat'],'fixed']
        flat.append({k:r[k] for k in ('id','seed','barrier','layout','repeat','order_position','method','paths','steps')} |
                    {'prepared_ms':r['prepared_ns']/1e6,'complete_ms':r['complete']['complete_ns']/1e6,
                     'generation_ms':r['complete']['generation_ns']/1e6,'layout_ms':r['complete']['layout_ns']/1e6,
                     'valuation_phase_ms':r['complete']['output_allocation_bridge_compute_ns']/1e6,
                     'prepared_change_vs_scalar_percent':matched_effect(r['prepared_ns'],scalar['prepared_ns']),
                     'complete_change_vs_scalar_percent':matched_effect(r['complete']['complete_ns'],scalar['complete']['complete_ns']),
                     'logical_occupancy':r['useful_lane_steps']/r['available_lane_steps']})
        if r['method']=='refill':
            effects.append(dict(seed=r['seed'],barrier=r['barrier'],layout=r['layout'],repeat=r['repeat'],
                                fixed_id=fixed['id'],refill_id=r['id'],fixed_ms=fixed['prepared_ns']/1e6,refill_ms=r['prepared_ns']/1e6,
                                prepared_change_percent=matched_effect(r['prepared_ns'],fixed['prepared_ns']),
                                complete_change_percent=matched_effect(r['complete']['complete_ns'],fixed['complete']['complete_ns'])))
    grouped=[];per_seed=[]
    for layout,barrier,method in itertools.product(('path','step'),BARRIERS,METHODS):
        chosen=[r for r in flat if (r['layout'],r['barrier'],r['method'])==(layout,barrier,method)]
        grouped.append(dict(layout=layout,barrier=barrier,method=method,**{k:summary(r[k] for r in chosen) for k in ('prepared_ms','complete_ms','generation_ms','layout_ms','valuation_phase_ms','prepared_change_vs_scalar_percent','complete_change_vs_scalar_percent')}))
        for seed in SEEDS:
            seed_rows=[r for r in chosen if r['seed']==seed]
            rec=dict(seed=seed,layout=layout,barrier=barrier,method=method)
            for scope in ('prepared','complete'):
                v=summary(r[scope+'_ms'] for r in seed_rows)
                rec.update({scope+'_'+k:value for k,value in v.items()})
                rec[scope+'_range_over_median']=(v['maximum']-v['minimum'])/v['median']
            per_seed.append(rec)
    diagnostics=[];survival=[]
    for barrier in BARRIERS:
        lives=[];hits=[]
        for seed in SEEDS:
            life=np.fromfile(run/f'ref-{seed}-{barrier}.lifetimes.u64',dtype='<u8')
            hit=np.fromfile(run/f'ref-{seed}-{barrier}.knocked.u8',dtype='u1')
            assert len(life)==len(hit)==100000
            counts=survival_counts(life,hit,252)
            for day,count in enumerate(counts):survival.append(dict(seed=seed,barrier=barrier,day=day,survivors=int(count),unique_paths=100000))
            lives.append(life);hits.append(hit)
        total_life=np.concatenate(lives);total_hit=np.concatenate(hits)
        rec=dict(barrier=barrier,unique_paths=300000,mean_dates=float(total_life.mean()),knocked_out_fraction=float(total_hit.mean()))
        for method in ('fixed','refill'):
            rec[method]=pooled_work(rows,barrier,method)
            assert rec[method]['useful']==int(total_life.sum())
        diagnostics.append(rec)
    write_csv(out/'observations.csv',flat);write_csv(out/'matched-effects.csv',effects);write_csv(out/'within-seed.csv',per_seed);write_csv(out/'survival.csv',survival)
    comparison_figure(rows,diagnostics,out)
    costs=cost_figure(rows,out);write_csv(out/'pooled-phase-means.csv',costs)
    per_case_costs=[]
    for layout,barrier,method in itertools.product(('path','step'),BARRIERS,METHODS):
        selected=[r['complete'] for r in rows if (r['layout'],r['barrier'],r['method'])==(layout,barrier,method)]
        per_case_costs.append(dict(layout=layout,barrier=barrier,method=method,observations=18,**mean_phases(selected)))
    write_csv(out/'case-phase-means.csv',per_case_costs)
    example=stock_figure(run,manifest,out)
    diagnostic_figure(rows,manifest,out)
    for ext in ('png','svg'):
        shutil.copyfile(a.mechanism/f'simd-mechanism-explained.{ext}',out/f'02-simd-mechanism.{ext}')
    shutil.copyfile(a.mechanism/'simd-mechanism-explained-data.json',out/'mechanism-example.json')
    for path,checksum in input_hashes.items():assert digest(path)==checksum,'input evidence changed'
    effect_summaries=[]
    for layout,barrier in itertools.product(('path','step'),BARRIERS):
        chosen=[e for e in effects if (e['layout'],e['barrier'])==(layout,barrier)]
        effect_summaries.append(dict(layout=layout,barrier=barrier,prepared_change_percent=summary(e['prepared_change_percent'] for e in chosen),complete_change_percent=summary(e['complete_change_percent'] for e in chosen)))
    result=dict(date='2026-11-14',status='Summary of the main pricing benchmark',
                new_measurements=False,source_campaign=str(run.relative_to(ROOT)),command=[sys.executable,*sys.argv],
                script_sha256=digest(Path(__file__)),input_sha256=input_hashes,grouped=grouped,within_seed=per_seed,
                path_diagnostics=diagnostics,phase_means=costs,per_case_phase_means=per_case_costs,effect_summaries=effect_summaries,
                definitions={'comparison':'All 18 fixed/refill observations per case. Faint lines match seed/repeat across separate sequential processes; thick line joins pooled absolute-time medians. Gray dashed line is scalar median.',
                             'effects':'100*(candidate/fixed-1), summarized as median of matched changes, not percent change between pooled medians.',
                             'phase_cards':'54 observations per layout/method, pooled equally across all three barriers, three seeds and six repeats. Arithmetic phase means add to mean whole interval.',
                             'logical_occupancy':'Sum useful / sum available lane slots across each unique seed exactly once; repeats/layouts do not create new paths.',
                             'example':'First six retained path IDs in seed 11 at barrier 120; schematic mechanism is separately labelled invented teaching workload.'},
                limits=['Only three input seeds; repeated process timings are not independent new workloads.',
                        'One-minute load rose from 3.68 at entry to a maximum 16.56; no samples excluded or replaced.',
                        'No affinity/frequency/thermal control. Process inspection denied; thermal query failed.',
                        'No confidence intervals, p-values, tail estimates or causal hardware attribution. No precise crossover claim.',
                        'Generation uses NumPy and a C++ bridge. Complete scope is not exchange latency or an all-C++ production engine.'],
                versions=dict(python=sys.version,numpy=np.__version__,matplotlib=matplotlib.__version__,platform=platform.platform()),
                typography=STYLE['typography'],
                fonts={name:dict(path=fm.findfont(prop),sha256=digest(Path(fm.findfont(prop)))) for name,prop in (('heading',HEAD),('body',BODY))},
                checks=['324 unique observations, exact full matrix','Every complete interval equals its phase sum','Logical work consistent across repeated layouts and equal to reference lifetimes',
                        'Survival boundary counts include final-date knockout versus maturity survivor','All fixed/refill points fit common 0–60 ms axes','Every phase card uses additive means from whole observations',
                        'All six illustrated stopping decisions and payoffs agree exactly','All input hashes unchanged; supplied mechanism assets copied unchanged'])
    assert all(r['prepared_ns']/1e6<=60 for r in rows if r['method']!='scalar')
    (out/'main_views.py').write_bytes(Path(__file__).read_bytes())
    result['artifacts']={p.name:digest(p) for p in sorted(out.iterdir()) if p.is_file()}
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(output=str(out),observations=len(rows),matched_comparisons=len(effects),figures=8,new_measurements=False,checks='passed')))


if __name__=='__main__':
    main()
