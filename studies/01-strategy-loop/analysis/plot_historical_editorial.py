"""Draw the QQQ profile cards and the traversal timing comparison."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics as stats
from plot import style, PALETTE as P, save
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyBboxPatch
import numpy as np

STUDY = Path(__file__).resolve().parents[1]
ROOT = STUDY.parents[1]

PROFILES=('jump','directional','low-directionality')
LABELS={'jump':'Largest gap','directional':'Most directional','low-directionality':'Least directional'}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def rows(path):
    with path.open() as f:
        return list(csv.DictReader(f))

def date(epoch):
    return datetime.fromtimestamp(epoch,timezone.utc).strftime('%d %b %Y')

def canvas(height):
    fig=plt.figure(figsize=(12,height))
    ax=fig.add_axes([0,0,1,1]);ax.set(xlim=(0,12),ylim=(0,height));ax.axis('off')
    return fig,ax

def txt(ax,x,y,label,size=12,color=None,**kw):
    return ax.text(x,y,label,fontsize=size,color=color or P['ink'],va='center',**kw)

def profile_cards(out,manifest,campaign,profiles,serif,provenance):
    fig,art=canvas(9.4)
    txt(art,.62,8.87,'Different paths. Similar trading activity.',29,fontfamily=serif)
    txt(art,.64,8.40,'Three price-selected QQQ windows · 32,768 available minute bars · 1,128 independent accounts',11)
    txt(art,3.16,7.96,'PRICE  /  FIRST CLOSE = 100',9,P['blue'])
    txt(art,10.08,7.96,'POSITION CHANGES',9,P['red'],ha='center')
    cmap=LinearSegmentedColormap.from_list('paper-activity',[P['paper'],P['red']])
    for i,p in enumerate(PROFILES):
        y=5.45-i*2.14
        art.add_patch(FancyBboxPatch((.62,y),10.76,2.01,
            boxstyle='round,pad=.015,rounding_size=.1',facecolor=P['panel'],edgecolor='none'))
        d=next(d for d in manifest['datasets'] if (d['profile'],d['bars'])==(p,32768))
        path=campaign/d['file']
        assert digest(path)==d['file_sha256']
        provenance[d['file']]=digest(path)
        close=np.array([float(r['close']) for r in rows(path)])
        pm=json.loads((profiles/'manifest.json').read_text())
        pd=next(r for r in pm['datasets'] if r['dataset_id']==d['dataset_id'])
        report_path=profiles/pd['file']
        assert digest(report_path)==pd['file_sha256']
        provenance['profiles/'+pd['file']]=digest(report_path)
        report=json.loads(report_path.read_text())
        a=next(r for r in report['aggregates'] if r['configs']==1128)
        assert abs(a['changes']/a['strategy_bars']*1000-a['changes_per_1000'])<1e-12
        txt(art,.85,y+1.69,f'0{i+1}',10,P['muted'])
        label={'jump':'Largest gap','directional':'Most\ndirectional','low-directionality':'Least\ndirectional'}[p]
        txt(art,.85,y+1.14,label,20,fontfamily=serif,linespacing=1.12)
        txt(art,.85,y+.42,f'{date(d["start"])}\nto {date(d["end"])}',10,P['muted'],linespacing=1.5)
        ax=fig.add_axes([3.16/12,(y+.54)/9.4,5.24/12,1.28/9.4])
        ax.set_facecolor(P['panel'])
        values=100*close/close[0]
        ax.fill_between(np.arange(len(close)),100,values,color=P['blue'],alpha=.07)
        ax.plot(values,color=P['blue'],lw=1.0)
        ax.axhline(100,color=P['rule'],lw=.8,zorder=0)
        ax.set(xlim=(0,32767),ylim=(75,120),yticks=[80,100,120],xticks=[])
        ax.tick_params(axis='y',length=0,labelsize=9,pad=5)
        for spine in ax.spines.values():spine.set_visible(False)
        b=a['blocks'];bounds=[r['start_bar'] for r in b]+[b[-1]['start_bar']+b[-1]['bars']]
        assert all(bounds[j+1]-bounds[j]==b[j]['bars'] for j in range(len(b)))
        assert max(r['changes_per_1000'] for r in b)<=50
        strip=fig.add_axes([3.16/12,(y+.28)/9.4,5.24/12,.12/9.4])
        strip.pcolormesh(bounds,[0,1],np.array([[r['changes_per_1000'] for r in b]]),
                         cmap=cmap,vmin=0,vmax=50,shading='flat')
        strip.set(xlim=(0,32768),ylim=(0,1));strip.axis('off')
        txt(art,3.16,y+.12,'0',8,P['muted'])
        txt(art,8.40,y+.12,'32,768 bars',8,P['muted'],ha='right')
        txt(art,10.08,y+1.32,f'{a["changes_per_1000"]:.1f}',38,P['red'],ha='center',fontfamily=serif)
        txt(art,10.08,y+.80,'changes per\n1,000 updates',12,ha='center',linespacing=1.25)
        txt(art,10.08,y+.28,f'{a["long_fraction"]:.1%} of updates\nhold QQQ',10,P['muted'],ha='center',linespacing=1.15)
    txt(art,.65,.81,'Activity strips: changes / 1,000 updates · blocks of up to 256 bars',11)
    legend=fig.add_axes([8.32/12,.71/9.4,2.15/12,.11/9.4]);legend.imshow(np.arange(256)[None,:],cmap=cmap,aspect='auto');legend.axis('off')
    txt(art,8.12,.765,'0',9,P['muted'],ha='right');txt(art,10.61,.765,'50',9,P['muted'])
    txt(art,.65,.44,'About 2% of updates change position in each window. Initial entries count; final liquidation does not.',10,P['muted'])
    txt(art,.65,.16,'ONCE IN A RUNTIME  /  RETAINED HISTORICAL DATA  /  SESSION GAPS RETAINED; THE AXIS COUNTS AVAILABLE BARS',8,P['muted'])
    save(fig,out,'05-historical-profiles')


def crossover(out,data,summary,serif):
    fig,art=canvas(10.7)
    txt(art,.64,10.12,'Change the storage. Watch the winner switch.',28,fontfamily=serif)
    txt(art,.66,9.61,'Directional window · 32,768 bars · 1,128 strategies · identical account results',12)
    txt(art,.66,9.14,'●  Strategy-first',12,P['blue']);txt(art,3.0,9.14,'●  Event-first',12,P['red'])
    txt(art,11.30,9.14,'Lower time is better',11,P['muted'],ha='right')
    ax=fig.add_axes([.25,.43,.50,.37]);ax.set_facecolor(P['paper'])
    ax.set(xlim=(-.08,1.08),ylim=(0,92),xticks=[0,1],yticks=[0,20,40,60,80])
    ax.set_xticklabels(['History together','Snapshot together'],fontfamily=serif,fontsize=18)
    txt(art,.66,8.63,'PREPARED TIME · MS',9,P['muted'])
    ax.grid(axis='y',color=P['rule'],alpha=.35,lw=.7);ax.set_axisbelow(True)
    ax.tick_params(axis='x',length=0,pad=13)
    for s in ('left','right','top'):ax.spines[s].set_visible(False)
    for order,color in [('strategy',P['blue']),('event',P['red'])]:
        values=[]
        for layout in ('history','snapshot'):
            cell=sorted([r for r in data if (r['profile'],int(r['bars']),int(r['configs']),r['order'],r['layout'])==('directional',32768,1128,order,layout)],key=lambda r:int(r['repeat']))
            assert [int(r['repeat']) for r in cell]==list(range(8))
            values.append([int(r['prepared_ns'])/1e6 for r in cell])
        for repeat in range(8):
            ax.plot([0,1],[values[0][repeat],values[1][repeat]],color=color,alpha=.10,lw=.7)
        med=[stats.median(v) for v in values]
        ax.plot([0,1],med,color=color,lw=2.7,zorder=3)
        for x,vals in enumerate(values):
            ax.scatter(x+np.linspace(-.018,.018,8),vals,s=22,facecolor=P['paper'],edgecolor=color,lw=.9,zorder=4)
            ax.scatter([x],[med[x]],s=80,color=color,zorder=5)
            offset=(18,0) if x==1 else ((12,-16) if order=='strategy' else (12,12))
            alignment='center' if x==1 else ('top' if order=='strategy' else 'bottom')
            ax.annotate(f'{med[x]:.2f} ms',(x,med[x]),xytext=offset,textcoords='offset points',ha='left',va=alignment,fontsize=16,color=color,fontfamily=serif,
                        bbox=dict(facecolor=P['paper'],edgecolor='none',pad=2))
    txt(art,3.48,4.09,'Strategy-first wins',12,P['blue'],ha='center')
    txt(art,8.52,4.09,'Event-first wins',12,P['red'],ha='center')
    art.plot([.65,11.35],[3.66,3.66],color=P['rule'],lw=1)
    txt(art,.66,3.31,'The same reversal in all 12 workloads',21,fontfamily=serif)
    txt(art,.66,2.97,'Each cell: history → snapshot, using the median paired strategy / event time ratio',10,P['muted'])
    centers=(4.72,7.38,10.03)
    for x,p in zip(centers,PROFILES):txt(art,x,2.56,LABELS[p],12,ha='center')
    settings=((4096,64),(4096,1128),(32768,64),(32768,1128))
    for ri,(n,k) in enumerate(settings):
        y=2.18-ri*.37
        txt(art,.72,y,f'{n:,} bars · {k:,} strategies',11,P['baseline'])
        art.plot([.68,11.32],[y-.185]*2,color=P['rule'],lw=.5,alpha=.6)
        for x,p in zip(centers,PROFILES):
            ratios=[]
            for layout in ('history','snapshot'):
                r=next(r for r in summary['ratios'] if (r['profile'],r['bars'],r['configs'],r['layout'])==(p,n,k,layout))
                ratios.append(r['median_ratio'])
            assert ratios[0]<1<ratios[1]
            txt(art,x-.42,y,f'{ratios[0]:.2f}',13,P['blue'],ha='center',weight='bold')
            txt(art,x,y,'→',12,P['muted'],ha='center')
            txt(art,x+.42,y,f'{ratios[1]:.2f}',13,P['red'],ha='center',weight='bold')
    txt(art,.66,.66,'Ratios below 1 favor strategy-first; above 1 favor event-first. All 384 observations contribute to the table.',9,P['muted'])
    txt(art,.66,.38,'Top: 8 observations per endpoint. Thin lines pair repeats; thick lines join medians. Preparation excluded. M3 / GCC 16.2 / AC.',9,P['muted'])
    txt(art,.66,.13,'ONCE IN A RUNTIME  /  RETAINED MEASUREMENTS  /  THE LINES CONNECT TWO DISCRETE STORAGE CHOICES',8,P['muted'])
    save(fig,out,'06-historical-ratios')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign',type=Path,required=True);parser.add_argument('--profiles',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    summary_path = STUDY / 'results/historical-summary.json'
    csv_path = STUDY / 'results/historical-observations.csv'
    summary=json.loads(summary_path.read_text());data=rows(csv_path)
    manifest=json.loads((args.campaign/'manifest.json').read_text())
    assert digest(args.campaign/'manifest.json')==summary['campaign_manifest_sha256']
    assert json.loads((args.profiles/'manifest.json').read_text())['input_manifest_sha256']==summary['input_manifest_sha256']
    assert len(data)==384
    assert len({(r['profile'],r['bars'],r['configs'],r['order'],r['layout'],r['repeat']) for r in data})==384
    for r in summary['ratios']:
        cell=[v for v in data if (v['profile'],int(v['bars']),int(v['configs']),v['layout'])==(r['profile'],r['bars'],r['configs'],r['layout'])]
        ratios=[]
        for repeat in range(8):
            pair={v['order']:int(v['prepared_ns']) for v in cell if int(v['repeat'])==repeat}
            assert set(pair)=={'strategy','event'}
            ratios.append(pair['strategy']/pair['event'])
        assert ratios==r['matched_ratios'] and stats.median(ratios)==r['median_ratio']
    provenance={'historical-summary.json':digest(summary_path),'historical-observations.csv':digest(csv_path)}
    serif=style()
    profile_cards(args.output,manifest,args.campaign,args.profiles,serif,provenance)
    crossover(args.output,data,summary,serif)
    metadata={'kind':'approved editorial figures using existing evidence','source_sha256':provenance,'generator_sha256':digest(Path(__file__)),'style':json.loads((ROOT/'publication/visual-style.json').read_text())['id'],'timing_observations':384}
    (args.output/'historical-editorial-figures.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print('Rendered two approved figures; verified 384 observations, 24 paired-ratio summaries, and profile input hashes.')

if __name__=='__main__':main()
