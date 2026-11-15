"""Audit a complete precision comparison and export descriptive tables/figures."""
import argparse
import csv
import json
from pathlib import Path
import shutil

import numpy as np
from precision_model import errors
from run_pilot import digest


def paired_changes(rows):
    lookup={}
    for row in rows:
        key=tuple(row[k] for k in ('seed','barrier','layout','repeat','method','precision'))
        if key in lookup:raise ValueError('duplicate precision observation')
        lookup[key]=row
    effects=[]
    for key,double in lookup.items():
        if key[-1]!='f64':continue
        if key[:-1]+('f32',) not in lookup:raise ValueError('missing precision partner')
        single=lookup[key[:-1]+('f32',)]
        if double['timed'] is not single['timed']:raise ValueError('mixed timing scope')
        if not double['timed']:continue
        if double['prepared_ns']<=0 or single['prepared_ns']<=0:raise ValueError('nonpositive prepared duration')
        effects.append({k:double[k] for k in ('seed','barrier','layout','repeat','method')} |
                       dict(f64_id=double['id'],f32_id=single['id'],f64_ns=double['prepared_ns'],
                            f32_ns=single['prepared_ns'],change_percent=100*(single['prepared_ns']/double['prepared_ns']-1)))
    # Every FP32 observation must also have exactly one FP64 counterpart.
    for key in lookup:
        if key[:-1]+('f64',) not in lookup or key[:-1]+('f32',) not in lookup:raise ValueError('missing precision partner')
    return effects


def csv_write(path,rows):
    if not rows:return
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def render(output,effects,accuracy,config):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager as fm
    from matplotlib.lines import Line2D
    from matplotlib.ticker import MaxNLocator
    paper,ink,blue,red,gray,rule='#FCE9D7','#0F0F0F','#003C7F','#BF0000','#3F3F3F','#C1B3A5'
    head=fm.FontProperties(family=['Georgia','DejaVu Serif'],weight='bold',style='italic')
    plt.rcParams.update({'font.family':['Arial','DejaVu Sans'],'font.size':11,'text.color':ink,
                         'figure.facecolor':paper,'axes.facecolor':paper,'svg.fonttype':'path'})
    def clean(ax):
        for s in ax.spines.values():s.set_visible(False)
        ax.tick_params(length=0,pad=7);ax.set_axisbelow(True)
    def save(fig,name):
        for ext in ('png','svg'):fig.savefig(output/f'{name}.{ext}',dpi=150,facecolor=paper)
        plt.close(fig)
    if effects:
        fig,axes=plt.subplots(len(config['barriers']),2,figsize=(13,10),squeeze=False,sharex=True)
        fig.subplots_adjust(left=.12,right=.96,bottom=.19,top=.76,hspace=.48,wspace=.24)
        fig.text(.055,.94,'Four floats. Two doubles. What changed?',fontproperties=head,fontsize=30)
        fig.text(.055,.879,'Each point compares FP32 with FP64 for the same method, seed, repeat and input layout.',fontsize=12)
        fig.text(.055,.839,'Left = float faster · 0 = same time · right = float slower. Precision and input storage both change.',fontsize=11)
        fig.legend(handles=[Line2D([0],[0],color=c,marker='o',lw=0,label=m) for m,c in [('Scalar',gray),('Fixed SIMD',blue),('Refill SIMD',red)]],
                   loc='upper left',bbox_to_anchor=(.045,.82),ncol=3,frameon=False)
        all_values=[r['change_percent'] for r in effects]
        low=min(-5.,min(all_values));high=max(5.,max(all_values));margin=.08*(high-low)
        for ri,barrier in enumerate(config['barriers']):
            for ci,layout in enumerate(config['layouts']):
                ax=axes[ri,ci]
                for mi,(method,color) in enumerate([('scalar',gray),('fixed',blue),('refill',red)]):
                    selected=[r for r in effects if (r['barrier'],r['layout'],r['method'])==(barrier,layout,method)]
                    values=[r['change_percent'] for r in selected]
                    if not values:continue
                    for row in selected:
                        si=config['seeds'].index(row['seed'])
                        y=2-mi+(si-1)*.12+(row['repeat']-(config['repeats']-1)/2)*.022
                        ax.scatter(row['change_percent'],y,s=17,color=color,alpha=.6,lw=0)
                    ax.plot([min(values),max(values)],[2-mi,2-mi],color=color,lw=.8)
                    ax.scatter(np.median(values),2-mi,marker='D',s=42,color=color,zorder=5)
                ax.axvline(0,color=ink,lw=.8,ls='--')
                ax.set_yticks((2,1,0),('Scalar','Fixed','Refill'));ax.set_ylim(-.4,2.4)
                ax.set_xlim(low-margin,high+margin)
                ax.set_title(f'Barrier {barrier} · {layout}-major',loc='left',fontproperties=head,fontsize=16)
                ax.grid(axis='x',color=rule,alpha=.35);clean(ax)
                if ri==len(config['barriers'])-1:ax.set_xlabel('Change in prepared runtime (%)',labelpad=9)
        fig.text(.055,.105,'Diamonds: median matched change. Lines: observed minimum–maximum, not confidence intervals.',fontsize=10)
        fig.text(.055,.069,'Prepared calculation includes payoff writes and ordered FP64 reduction. Generation, casting and layout conversion are excluded.',fontsize=10)
        fig.text(.055,.036,f"{config['paths']:,} paths × {config['steps']} dates · {len(config['seeds'])} unique seeds · {config['repeats']} fresh-process repeats · descriptive pilot",fontsize=10)
        save(fig,'runtime-comparison')
    total=[r for r in accuracy if r['comparison']=='total-f32-vs-f64']
    fig,axes=plt.subplots(1,2,figsize=(12,8.5),gridspec_kw={'width_ratios':[1,1.25]})
    fig.subplots_adjust(left=.19,right=.94,bottom=.23,top=.72,wspace=.50)
    fig.text(.055,.94,'Did the answer change?',fontproperties=head,fontsize=32)
    fig.text(.055,.873,'Every path is checked. A small average error can conceal a changed knock-out decision.',fontsize=12)
    y=np.arange(len(total))[::-1]
    axes[0].barh(y,[r['knockout_disagreements'] for r in total],height=.42,color=red)
    for yy,row in zip(y,total):
        axes[0].annotate(str(row['knockout_disagreements']),(row['knockout_disagreements'],yy),xytext=(5,0),textcoords='offset points',va='center',fontsize=10)
    axes[0].set_xlim(0,max(1,max(r['knockout_disagreements'] for r in total))*1.3)
    axes[0].xaxis.set_major_locator(MaxNLocator(integer=True))
    axes[0].set_yticks(y,[f"B{r['barrier']} · seed {r['seed']}" for r in total])
    axes[0].set_xlabel('Paths with different knock-out decisions',labelpad=12,fontsize=10)
    axes[0].set_title('Classification',loc='left',fontproperties=head,fontsize=19)
    axes[1].axvline(0,color=blue,lw=1,ls='--')
    values=[r['price_difference'] for r in total]
    axes[1].scatter(values,y,color=red,s=36)
    for yy,value in zip(y,values):axes[1].annotate(f'{value:+.3g}',(value,yy),xytext=(6,6),textcoords='offset points',fontsize=9)
    bound=max(1e-12,max(abs(v) for v in values))*1.4
    axes[1].set_xlim(-bound,bound);axes[1].set_yticks([])
    axes[1].ticklabel_format(axis='x',style='sci',scilimits=(-3,3),useMathText=True)
    axes[1].set_xlabel('FP32 estimate − FP64 estimate · price units',labelpad=12,fontsize=10)
    axes[1].set_title('Estimated option value',loc='left',fontproperties=head,fontsize=19)
    for ax in axes:ax.set_ylim(-.7,len(total)-.3);ax.grid(axis='x',color=rule,alpha=.35);clean(ax)
    fig.text(.055,.139,'FP32 uses float factors, path updates and payoffs; both versions average in ascending-ID double precision.',fontsize=10)
    fig.text(.055,.100,'Accuracy is counted once per unique seed/barrier. Repeated timings do not create additional independent price samples.',fontsize=10)
    fig.text(.055,.061,'Maximum/RMS payoff errors and the rounded-input diagnostic are retained in accuracy.csv. No accuracy threshold is assumed.',fontsize=10)
    fig.text(.055,.025,f"{config['paths']:,} paths per seed · synthetic scenarios · FP64 is a numerical reference, not an exact market price.",fontsize=10)
    save(fig,'accuracy-comparison')
    return dict(heading_font=fm.findfont(head),heading_font_sha256=digest(Path(fm.findfont(head))),matplotlib=matplotlib.__version__)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();source=args.input.resolve();output=args.output.resolve()
    manifest=json.loads((source/'manifest.json').read_text())
    if manifest['status']!='complete' or manifest.get('final_integrity')!='passed':raise ValueError('requires a complete audited precision run')
    rows=json.loads((source/'observations.json').read_text())
    if len(rows)!=manifest['expected_observations'] or len(rows)!=manifest['observations']:raise ValueError('incomplete observation matrix')
    before={name:digest(source/name) for name in ('manifest.json','observations.json')}
    for group in ('datasets','references'):
        for record in manifest[group]:
            for item in record.get('files',[record]):
                if digest(source/item['name'])!=item['sha256']:raise ValueError('source input/reference checksum mismatch')
    executions={r['id']:r for r in manifest['executions']}
    for row in rows:
        record=executions[row['id']]
        stdout=source/(row['id']+'.stdout.json')
        if digest(stdout)!=record['stdout_sha256']:raise ValueError('observation log hash mismatch')
        actual=json.loads(stdout.read_text())
        if any(actual[k]!=row[k] for k in actual):raise ValueError('observation differs from raw log')
        for item in record['audited_outputs']:
            if digest(source/item['name'])!=item['sha256']:raise ValueError('payoff/date/knockout hash mismatch')
    accuracy=[]
    for seed in manifest['config']['seeds']:
        for barrier in manifest['config']['barriers']:
            refs={}
            for precision in ('f64','f32','f64-rounded'):
                suffix='f32' if precision=='f32' else 'f64'
                prefix=source/f'ref-{seed}-{barrier}-{precision}'
                refs[precision]=tuple(np.fromfile(str(prefix)+'.'+name,dtype=dtype) for name,dtype in
                                      ((f'payoffs.{suffix}','<f4' if suffix=='f32' else '<f8'),('lifetimes.u64','<u8'),('knocked.u8','u1')))
            for comparison,candidate,reference in (('total-f32-vs-f64','f32','f64'),('input-rounding-only','f64-rounded','f64'),('remaining-arithmetic','f32','f64-rounded')):
                accuracy.append(dict(seed=seed,barrier=barrier,comparison=comparison,**errors(refs[candidate],refs[reference])))
    if accuracy!=manifest['accuracy']:raise ValueError('accuracy summaries differ from retained references')
    effects=paired_changes(rows);summaries=[]
    for barrier in manifest['config']['barriers']:
        for layout in manifest['config']['layouts']:
            for method in manifest['config']['methods']:
                selected=[r['change_percent'] for r in effects if (r['barrier'],r['layout'],r['method'])==(barrier,layout,method)]
                if selected:summaries.append(dict(barrier=barrier,layout=layout,method=method,observations=len(selected),
                                                  median_matched_change_percent=float(np.median(selected)),minimum_percent=min(selected),maximum_percent=max(selected)))
    output.mkdir(parents=True,exist_ok=False)
    csv_write(output/'accuracy.csv',accuracy);csv_write(output/'matched-runtime.csv',effects);csv_write(output/'runtime-summary.csv',summaries)
    fonts=render(output,effects,accuracy,manifest['config'])
    shutil.copyfile(Path(__file__),output/'analyze_precision.py')
    for name,h in before.items():
        if digest(source/name)!=h:raise ValueError('raw run changed during analysis')
    summary=dict(status='complete',timed=manifest['timed'],new_measurements=False,
                 source=str(source),source_sha256=before,analysis_sha256=digest(Path(__file__)),
                 native_types=manifest['native_types'],runtime_summaries=summaries,accuracy=accuracy,fonts=fonts,
                 checks=['Raw observations agree with individual worker logs','Every retained input/reference/output hash checked',
                         'Accuracy recomputed from individual path outputs','Matched ratio denominator and identity checked',
                         'Untimed verification produces no runtime comparisons','Raw run remains unchanged'],
                 artifacts={p.name:digest(p) for p in sorted(output.iterdir())})
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(dict(output=str(output),timed=manifest['timed'],matched_runtime_observations=len(effects),new_measurements=False)))


if __name__=='__main__':main()
