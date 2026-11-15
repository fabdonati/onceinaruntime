"""Render checked pilot/main observations. Refuses incomplete or unverified runs."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import platform
import statistics
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib import font_manager
import numpy as np

from run import CANDIDATES, audit_rows, digest, plan, read_rows, validate_config

ROOT = Path(__file__).resolve().parents[3]
PALETTE = json.loads((ROOT/'publication/visual-style.json').read_text())['palette']


def load_run(path, timed=True, main=False):
    manifest = json.loads((path/'manifest.json').read_text())
    kind = ('main measurement' if main else 'timing pilot') if timed else 'untimed matrix verification'
    if manifest.get('status') != 'complete' or manifest.get('timed') is not timed or manifest.get('kind') != kind:
        raise ValueError('figures require a complete run of the requested kind')
    cfg = manifest['config']
    validate_config(cfg)
    expected = plan(cfg, timed)
    observations = json.loads((path/'observations.json').read_text())
    if len(observations) != len(expected) or manifest['observations'] != len(expected):
        raise ValueError('incomplete observation matrix')
    for file in manifest['datasets']:
        for key in ('file','reference'):
            if digest(path/file[key]) != file[key+'_sha256']:
                raise ValueError('input/reference integrity mismatch')
    for row, item in zip(observations, expected):
        for key in ('id','bars','seed','configs','repeat','order_position','order','layout'):
            if row[key] != item[key]:
                raise ValueError('observation identity/order mismatch')
        raw = json.loads((path/(row['id']+'.stdout.json')).read_text())
        if any(raw[key] != row[key] for key in raw):
            raise ValueError('observation differs from worker output')
        summary = path/(row['id']+'.summary.csv')
        if digest(summary) != row['summary_sha256']:
            raise ValueError('summary hash mismatch')
        reference = read_rows(path/f'n{row["bars"]}-s{row["seed"]}.reference.csv')[:row['configs']]
        audit_rows(read_rows(summary),reference)
        if ((row['prepared_ns'] <= 0 if timed else row['whole_ns'] != 0) or
            row['prepared_ns'] != row['replay_ns']+row['summary_ns'] or
            row['whole_ns'] != sum(row[field+'_ns'] for field in ('feature','layout','setup','replay','summary'))):
            raise ValueError('invalid measured intervals')
    return manifest, observations


def style():
    names = {font.name for font in font_manager.fontManager.ttflist}
    serif = next((font for font in ('Georgia','Liberation Serif','DejaVu Serif') if font in names), 'DejaVu Serif')
    sans = next((font for font in ('Arial','Liberation Sans','DejaVu Sans') if font in names), 'DejaVu Sans')
    plt.rcParams.update({'figure.facecolor':PALETTE['paper'],'axes.facecolor':PALETTE['paper'],
                         'text.color':PALETTE['ink'],'axes.labelcolor':PALETTE['ink'],
                         'xtick.color':PALETTE['baseline'],'ytick.color':PALETTE['baseline'],
                         'font.family':sans,'font.size':11,'axes.spines.top':False,
                         'axes.spines.right':False,'axes.edgecolor':PALETTE['rule'],
                         'svg.fonttype':'path','savefig.facecolor':PALETTE['paper']})
    return serif


def label(fig, title, subtitle, serif, kind='PILOT'):
    fig.text(.07,.95,title,fontfamily=serif,fontsize=25,va='top')
    fig.text(.07,.905,subtitle,fontsize=11,color=PALETTE['baseline'],va='top')
    fig.text(.07,.025,f'ONCE IN A RUNTIME   /   {kind} · SYNTHETIC INPUT · NOT A MARKET BACKTEST',
             fontsize=9,color=PALETTE['baseline'])


def save(fig, output, name):
    for ext in ('png','svg'):
        fig.savefig(output/(name+'.'+ext),dpi=180)
    plt.close(fig)


def render_heatmap(path, output, cfg, rows, serif):
    target = next(row for row in rows if row['bars']==max(cfg['bars']) and row['seed']==cfg['seeds'][0]
                  and row['configs']==max(cfg['counts']))
    summaries = read_rows(path/(target['id']+'.summary.csv'))
    spans = cfg['spans']
    matrix = np.full((len(spans),len(spans)),np.nan)
    for row in summaries:
        matrix[spans.index(int(row['slow'])),spans.index(int(row['fast']))] = 100*float(row['net_return'])
    bound = max(1.,float(np.nanmax(np.abs(matrix))))
    fig, ax = plt.subplots(figsize=(10,8))
    fig.subplots_adjust(left=.12,right=.85,bottom=.14,top=.83)
    cmap = LinearSegmentedColormap.from_list('return',[PALETTE['red'],PALETTE['paper'],PALETTE['blue']])
    art = ax.imshow(matrix,origin='lower',cmap=cmap,norm=TwoSlopeNorm(vmin=-bound,vcenter=0,vmax=bound),interpolation='none')
    ticks = list(range(0,len(spans),8))+[len(spans)-1]
    ax.set_xticks(ticks,[str(spans[i]) for i in ticks]); ax.set_yticks(ticks,[str(spans[i]) for i in ticks])
    ax.set_xlabel('Fast EMA span · synthetic bars'); ax.set_ylabel('Slow EMA span · synthetic bars')
    ax.text(.62,.22,'One tile = one account\nSame invented price path\nSame fees and warm-up',
            transform=ax.transAxes,fontsize=12,linespacing=1.6)
    fig.colorbar(art,ax=ax,shrink=.65,pad=.04,label='Net period return (%) · synthetic example')
    label(fig,'A thousand versions of one rule',f'1,128 checked accounts · {target["bars"]:,} synthetic bars · seed {target["seed"]}',serif,'CHECKED EXAMPLE')
    save(fig,output,'01-synthetic-accounts')


def render_cost(output,cfg,rows,serif,kind='PILOT'):
    fig, axes = plt.subplots(2,2,figsize=(12,9),sharex=True,sharey=True)
    fig.subplots_adjust(left=.09,right=.96,top=.74,bottom=.14,hspace=.35,wspace=.16)
    for ni,n in enumerate(cfg['bars']):
        for li,layout in enumerate(('history','snapshot')):
            ax=axes[ni,li]
            for order,color,marker in (('strategy',PALETTE['blue'],'o'),('event',PALETTE['red'],'s')):
                for si,seed in enumerate(cfg['seeds']):
                    centers=[]
                    for k in cfg['counts']:
                        selected=[r for r in rows if (r['bars'],r['configs'],r['layout'],r['order'],r['seed'])==(n,k,layout,order,seed)]
                        values=[r['prepared_ns']/(k*r['eligible_bars']) for r in selected]
                        centers.append(statistics.median(values))
                        offsets=np.linspace(-.025,.025,len(values)) + (-.045 if order=='strategy' else .045)
                        xs=k*np.exp(offsets)
                        ax.scatter(xs,values,s=22,marker=marker,facecolors=color if si==0 else 'none',
                                   edgecolors=color,alpha=.55,linewidths=.8,zorder=3)
                    ax.plot(cfg['counts'],centers,color=color,lw=1.7,ls=('-', '--', ':')[si],
                            marker=marker,ms=4,label=f'{order.capitalize()}-first · seed {seed}')
            ax.set_xscale('log'); ax.set_xticks(cfg['counts'],[str(k) for k in cfg['counts']])
            ax.set_title(f'{layout.capitalize()}-contiguous · N = {n:,}',loc='left',fontsize=12,pad=10)
            ax.grid(axis='y',color=PALETTE['rule'],lw=.6,alpha=.5)
            ax.set_ylim(bottom=0)
            if li==0: ax.set_ylabel('ns / strategy-bar · lower is better')
            if ni==1: ax.set_xlabel('Independent configurations · K')
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,ncol=2,loc='upper left',bbox_to_anchor=(.07,.875),frameon=False,fontsize=10)
    label(fig,'Same accounts. Different routes.',
          f'48 shared EMA windows · dots: fresh processes · lines: {cfg["repeats"]}-run medians within each seed',serif,kind)
    save(fig,output,'03-replay-cost')


def render_whole(output,cfg,rows,serif,kind='PILOT'):
    # Largest history / smallest sweep makes the fixed preparation bill visible.
    # Figure 3 retains the complete matrix, so this selection hides no settings.
    selected=[r for r in rows if r['bars']==max(cfg['bars']) and r['configs']==min(cfg['counts']) and r['seed']==cfg['seeds'][0]]
    fig,ax=plt.subplots(figsize=(11,7))
    fig.subplots_adjust(left=.25,right=.95,top=.78,bottom=.25)
    representatives=[]
    for y,(order,layout) in enumerate(CANDIDATES):
        group=[r for r in selected if (r['order'],r['layout'])==(order,layout)]
        median=statistics.median(r['whole_ns'] for r in group)
        representative=min(group,key=lambda r:(abs(r['whole_ns']-median),r['id']))
        representatives.append(representative['id'])
        stages=[('Features',representative['feature_ns'],PALETTE['rule']),
                ('Layout',representative['layout_ns'],PALETTE['muted']),
                ('Accounts',representative['setup_ns'],PALETTE['panel']),
                ('Replay + summaries (order color)',representative['prepared_ns'],PALETTE['blue'] if order=='strategy' else PALETTE['red'])]
        left=0.
        for name,duration,color in stages:
            value=duration/1e6
            ax.barh(y,value,left=left,color=color,height=.45,edgecolor=PALETTE['paper'],linewidth=.6,label=name if y==0 else None)
            left+=value
        ax.scatter([r['whole_ns']/1e6 for r in group],[y-.32]*len(group),s=25,color=PALETTE['ink'],marker='|')
    ax.set_yticks(range(4),[f'{o.capitalize()}-first\n{l}-contiguous' for o,l in CANDIDATES])
    ax.invert_yaxis(); ax.set_xlim(left=0); ax.set_xlabel('Complete computation · milliseconds')
    ax.grid(axis='x',color=PALETTE['rule'],alpha=.4,lw=.6)
    handles,labels=ax.get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper left',bbox_to_anchor=(.065,.17),ncol=4,frameon=False,fontsize=9)
    label(fig,'Include the preparation bill',
          f'N = {max(cfg["bars"]):,} · K = {min(cfg["counts"]):,} · seed {cfg["seeds"][0]} · ticks: all {cfg["repeats"]} complete runs',serif,kind)
    fig.text(.07,.075,'Each stacked bar is one actual run nearest its group’s median total. CSV input/output is excluded.',fontsize=9)
    save(fig,output,'04-whole-run')
    return representatives


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--example',action='store_true',help='only the checked account heatmap, from untimed verification')
    mode.add_argument('--main',action='store_true',help='render a completed main campaign')
    args=parser.parse_args()
    manifest,rows=load_run(args.input, timed=not args.example,main=args.main)
    args.output.mkdir(parents=True,exist_ok=False)
    serif=style(); cfg=manifest['config']
    render_heatmap(args.input,args.output,cfg,rows,serif)
    if args.example:
        target=next(row for row in rows if row['bars']==max(cfg['bars']) and row['seed']==cfg['seeds'][0]
                    and row['configs']==max(cfg['counts']))
        source=args.input/(target['id']+'.summary.csv')
        (args.output/'accounts.csv').write_bytes(source.read_bytes())
        provenance=dict(command=[sys.executable,*sys.argv],kind='untimed synthetic account illustration',
                        input_manifest_sha256=digest(args.input/'manifest.json'),summary_sha256=digest(source),
                        source_sha256=digest(Path(__file__)),style_sha256=digest(ROOT/'publication/visual-style.json'),
                        python=sys.version,numpy=np.__version__,matplotlib=matplotlib.__version__,
                        headline_font=serif,bars=target['bars'],seed=target['seed'],configs=target['configs'],
                        spans=cfg['spans'],capital=cfg['capital'],fee=cfg['fee'],timed=False)
        (args.output/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
        print(json.dumps(dict(output=str(args.output),figures=1,timed=False),indent=2))
        return
    kind='MAIN RUN' if args.main else 'PILOT'
    render_cost(args.output,cfg,rows,serif,kind)
    representatives=render_whole(args.output,cfg,rows,serif,kind)
    with (args.output/'observations.csv').open('w',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)
    groups=[]
    for n in cfg['bars']:
        for seed in cfg['seeds']:
            for k in cfg['counts']:
                for order,layout in CANDIDATES:
                    selected=[r for r in rows if (r['bars'],r['seed'],r['configs'],r['order'],r['layout'])==(n,seed,k,order,layout)]
                    values=[r['prepared_ns']/(k*r['eligible_bars']) for r in selected]
                    groups.append(dict(bars=n,seed=seed,configs=k,order=order,layout=layout,n=len(values),
                                       median_ns_per_strategy_bar=statistics.median(values),min_ns_per_strategy_bar=min(values),
                                       max_ns_per_strategy_bar=max(values),median_whole_ms=statistics.median(r['whole_ns']/1e6 for r in selected)))
    with (args.output/'groups.csv').open('w',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=list(groups[0]),lineterminator='\n')
        writer.writeheader(); writer.writerows(groups)
    provenance=dict(command=[sys.executable,*sys.argv],input_manifest_sha256=digest(args.input/'manifest.json'),
                    input_observations_sha256=digest(args.input/'observations.json'),
                    source_sha256=digest(Path(__file__)),style_sha256=digest(ROOT/'publication/visual-style.json'),
                    python=sys.version,numpy=np.__version__,matplotlib=matplotlib.__version__,platform=platform.platform(),
                    headline_font=serif,representative_ids=representatives,
                    whole_run_workload_rule='Largest N, smallest K, first seed; expose fixed preparation cost. Figure 3 retains the full matrix.',
                    description=f'{kind}. {cfg["repeats"]} fresh-process samples per cell and seed. No confidence intervals or market inference.')
    (args.output/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(json.dumps(dict(output=str(args.output),figures=3,observations=len(rows)),indent=2))


if __name__=='__main__':
    main()
