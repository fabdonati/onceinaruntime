"""Audit retained historical workers and render the bounded QQQ study."""
import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics

from run import CANDIDATES, audit_rows, digest, plan, read_rows, validate_config, power_mode, power_ok
from plot import style, PALETTE as P, save
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
import matplotlib.tri as tri
import numpy as np
from plot_historical_editorial import profile_cards, crossover

LABELS={'jump':'Largest gap','directional':'Most directional','low-directionality':'Least directional'}


def load(path):
    m=json.loads((path/'manifest.json').read_text()); cfg=m['config'];validate_config(cfg)
    if not (m['status']=='complete' and m['final_integrity']=='passed' and m['timed'] and m['input_kind']=='historical'):
        raise ValueError('complete historical timing campaign required')
    if digest(path/'input-manifest.json')!=cfg['input_manifest_sha256']:
        raise ValueError('input manifest differs')
    if digest(path/'source.zip')!=m['source_archive_sha256'] or digest(path/'strategy_replay')!=m['binary_sha256']:
        raise ValueError('source/build snapshot differs')
    datasets={d['dataset_id']:d for d in m['datasets']}
    for d in datasets.values():
        for key in ('file','reference'):
            if digest(path/d[key])!=d[key+'_sha256']: raise ValueError('input/reference differs')
    rows=json.loads((path/'observations.json').read_text()); expected=plan(cfg,True)
    if len(rows)!=len(expected) or m['observations']!=len(rows): raise ValueError('incomplete matrix')
    identities={}
    executions={e['id']:e for e in m['executions']}
    for r,e in zip(rows,expected):
        if any(r[k]!=v for k,v in e.items()): raise ValueError('execution identity/order differs')
        if r['power_condition']!=m['power_condition']: raise ValueError('mixed power condition')
        rawpath=path/(r['id']+'.stdout.json');raw=json.loads(rawpath.read_text())
        if digest(rawpath)!=executions[r['id']]['stdout_sha256'] or any(raw[k]!=r[k] for k in raw):
            raise ValueError('worker output differs')
        summary=path/(r['id']+'.summary.csv'); fingerprint=digest(summary)
        if fingerprint!=r['summary_sha256']: raise ValueError('summary differs')
        key=(r['dataset_id'],r['configs'])
        if key in identities and identities[key]!=fingerprint: raise ValueError('variant outputs differ')
        identities[key]=fingerprint
        audit_rows(read_rows(summary),read_rows(path/datasets[r['dataset_id']]['reference'])[:r['configs']])
        if not (r['timed'] and r['prepared_ns']>0 and r['eligible_bars']==r['bars']-96 and r['windows']==48
                and r['prepared_ns']==r['replay_ns']+r['summary_ns']
                and r['whole_ns']==sum(r[k+'_ns'] for k in ('feature','layout','setup','replay','summary'))):
            raise ValueError('invalid intervals/dimensions')
    if any(not power_ok(s,True) or power_mode(s)!=m['power_condition'] for s in m['environment']):
        raise ValueError('power changed')
    return m,rows


def header(fig,title,subtitle,serif,power):
    fig.text(.07,.955,title,fontfamily=serif,fontsize=27,va='top')
    fig.text(.07,.90,subtitle,fontsize=11,va='top')
    fig.text(.07,.025,f'ONCE IN A RUNTIME   /   QQQ · ALPACA SIP · {power} POWER · APPLE M3 / GCC 16.2',fontsize=9,color=P['muted'])


def date_label(epoch):
    return datetime.fromtimestamp(epoch,timezone.utc).strftime('%d %b %Y')


def render_profiles(output,manifest,profiles_path,data_path,serif):
    profile_cards(output,manifest,data_path,profiles_path,serif,{})


def render_ratios(output,m,rows,serif):
    summaries=[]
    for k in m['config']['counts']:
        for n in m['config']['bars']:
            for p in m['config']['profiles']:
                for layout in ('history','snapshot'):
                    cell=[r for r in rows if (r['bars'],r['configs'],r['profile'],r['layout'])==(n,k,p,layout)]
                    ratios=[]
                    for repeat in range(m['config']['repeats']):
                        pair={r['order']:r['prepared_ns'] for r in cell if r['repeat']==repeat}
                        ratios.append(pair['strategy']/pair['event'])
                    summaries.append(dict(profile=p,bars=n,configs=k,layout=layout,
                        matched_ratios=ratios,median_ratio=statistics.median(ratios)))
    crossover(output,rows,dict(ratios=summaries),serif)
    return summaries


def render_whole(output,m,rows,serif):
    profile='directional'
    fig,ax=plt.subplots(figsize=(11,7))
    fig.subplots_adjust(left=.24,right=.94,bottom=.25,top=.72)
    longest=max(r['whole_ns']/1e6 for r in rows if (r['profile'],r['bars'],r['configs'])==(profile,32768,64))
    for y,(order,layout) in enumerate(CANDIDATES):
        cell=[r for r in rows if (r['profile'],r['bars'],r['configs'],r['order'],r['layout'])==(profile,32768,64,order,layout)]
        median=statistics.median(r['whole_ns'] for r in cell)
        representative=min(cell,key=lambda r:(abs(r['whole_ns']-median),r['repeat']))
        left=0; color=P['blue'] if order=='strategy' else P['red']
        for field,tint in [('feature','#D0C0B0'),('layout','#A89888'),('setup','#796C60'),('replay',color),('summary',P['ink'])]:
            width=representative[field+'_ns']/1e6
            ax.barh(y,width,left=left,height=.48,color=tint);left+=width
        ax.scatter([r['whole_ns']/1e6 for r in cell],[y+.32]*len(cell),marker='|',color=P['ink'],s=70,lw=1)
        ax.text(longest*1.03,y,f'{median/1e6:.2f} ms',va='center',fontsize=12)
    ax.set_xlim(0,longest*1.2);ax.set_xlabel('Complete computation · milliseconds');ax.grid(axis='x',alpha=.2,color=P['rule']);ax.set_axisbelow(True)
    ax.set_yticks(range(4),['Strategy / history','Event / history','Strategy / snapshot','Event / snapshot']);ax.invert_yaxis()
    header(fig,'Preparing the data is part of the bill','Directional profile · 32,768 bars · 64 strategies · labels show median complete time',serif,m['power_condition'])
    fig.text(.07,.16,'Gray: features, layout, setup     Blue/red: strategy/event replay     Black: summaries',fontsize=10)
    fig.text(.07,.11,'Each stack is an actual run nearest its median total. Ticks show all eight measured totals.',fontsize=10)
    fig.text(.07,.07,'CSV parsing and writing are outside the clock. The profile and workload were chosen before timing.',fontsize=9,color=P['muted'])
    save(fig,output,'07-historical-whole')


def render_accounts(output,m,path,serif):
    d=next(d for d in m['datasets'] if d['dataset_id']=='qqq-directional-n32768')
    rows=read_rows(path/d['reference'])
    fast,slow,returns=[np.array([float(r[k]) for r in rows]) for k in ('fast','slow','net_return')];returns*=100
    low=min(-5,5*np.floor(returns.min()/5)); high=max(5,5*np.ceil(returns.max()/5))
    norm=TwoSlopeNorm(vmin=low,vcenter=0,vmax=high)
    cmap=LinearSegmentedColormap.from_list('paper-returns',[P['red'],P['paper'],P['blue']])
    levels=np.concatenate((np.arange(low,0,5),np.arange(0,high+1,1)))
    fig,ax=plt.subplots(figsize=(11,9));fig.subplots_adjust(left=.10,right=.84,bottom=.19,top=.79)
    mesh=tri.Triangulation(fast,slow);art=ax.tricontourf(mesh,returns,levels=levels,cmap=cmap,norm=norm)
    contourlevels=[v for v in (-40,-20,-10,-5,0,2,4) if returns.min()<v<returns.max()]
    if len(contourlevels):
        contours=ax.tricontour(mesh,returns,levels=contourlevels,colors=P['ink'],linewidths=.45)
        ax.clabel(contours,fontsize=8,fmt=lambda x:f'{x:.0f}%')
    ax.set(xlim=(0,98),ylim=(0,98),xlabel='Fast EMA span · available bars',ylabel='Slow EMA span · available bars');ax.set_aspect('equal')
    ax.text(49,34,'One setting, one account',fontfamily=serif,fontsize=18)
    ax.text(49,19,'Blue = gain; red = loss.\nEvery account sees the same prices.\nEvery implementation must agree.',fontsize=10,linespacing=1.7)
    ax.text(49,8,'Blank: fast ≥ slow, excluded pairs.',fontsize=9,color=P['muted'])
    fig.colorbar(art,ax=ax,shrink=.75,pad=.05,spacing='proportional',ticks=[low,-40,-20,0,high],label='Model net period return (%)')
    header(fig,'A thousand versions of one rule',f'QQQ · {date_label(d["start"])} – {date_label(d["end"])} · 1,128 checked accounts',serif,m['power_condition'])
    fig.text(.07,.12,'Price-selected directional window; no selection by account return. One-basis-point fees on each side.',fontsize=10)
    fig.text(.07,.078,'Contours interpolate tested pairs. Color is centered at zero with unequal ranges; no dividends, spread or fill model.',fontsize=9,color=P['muted'])
    save(fig,output,'08-historical-accounts')
    with (output/'historical-accounts.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--profiles',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    m,rows=load(a.run)
    if m['config']['kind']!='historical strategy traversal main campaign': raise ValueError('main campaign required for final figures')
    profiles=json.loads((a.profiles/'manifest.json').read_text())
    if profiles['input_manifest_sha256']!=m['input_manifest_sha256']: raise ValueError('profile inputs differ')
    for d in profiles['datasets']:
        if digest(a.profiles/d['file'])!=d['file_sha256']: raise ValueError('profile report differs')
    a.output.mkdir(parents=True,exist_ok=True);serif=style()
    render_profiles(a.output,m,a.profiles,a.run,serif)
    ratios=render_ratios(a.output,m,rows,serif)
    render_whole(a.output,m,rows,serif);render_accounts(a.output,m,a.run,serif)
    groups=[]
    for profile in m['config']['profiles']:
        for n in m['config']['bars']:
            for k in m['config']['counts']:
                for order,layout in CANDIDATES:
                    cell=[r for r in rows if (r['profile'],r['bars'],r['configs'],r['order'],r['layout'])==(profile,n,k,order,layout)]
                    groups.append(dict(profile=profile,bars=n,configs=k,order=order,layout=layout,
                        prepared_median_ms=statistics.median(r['prepared_ns'] for r in cell)/1e6,
                        prepared_min_ms=min(r['prepared_ns'] for r in cell)/1e6,
                        prepared_max_ms=max(r['prepared_ns'] for r in cell)/1e6,
                        whole_median_ms=statistics.median(r['whole_ns'] for r in cell)/1e6))
    activity=[]
    for d in profiles['datasets']:
        report=json.loads((a.profiles/d['file']).read_text())
        for v in report['aggregates']:
            activity.append(dict(profile=d['profile'],bars=d['bars'],**{k:v[k] for k in ('configs','changes_per_1000','long_fraction','holding_bars','completed_spells','censored_spells')}))
    result=dict(input_manifest_sha256=m['input_manifest_sha256'],campaign_manifest_sha256=digest(a.run/'manifest.json'),analysis_sha256=digest(__file__),editorial_figure_analysis_sha256=digest(Path(__file__).with_name('plot_historical_editorial.py')),power_condition=m['power_condition'],observations=len(rows),groups=groups,ratios=ratios,activity=activity)
    (a.output/'historical-summary.json').write_text(json.dumps(result,indent=2)+'\n')
    with (a.output/'historical-observations.csv').open('w') as f:
        keys=['dataset_id','profile','bars','configs','repeat','order_position','order','layout','power_condition','prepared_ns','whole_ns','feature_ns','layout_ns','setup_ns','replay_ns','summary_ns','summary_sha256']
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows({k:r[k] for k in keys} for r in rows)
    print(json.dumps(dict(observations=len(rows),power=m['power_condition'],groups=len(groups),output=str(a.output))))


if __name__=='__main__':main()
