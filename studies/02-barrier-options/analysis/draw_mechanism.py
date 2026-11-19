"""Beginner-facing mechanism illustration. Invented teaching workload, no timings."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Rectangle, FancyBboxPatch
from matplotlib.colors import to_rgb

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
OUT=parser.parse_args().output.resolve()
OUT.mkdir(parents=True,exist_ok=False)
PAPER,INK,BLUE,RED,GRAY,PANEL,RULE='#FCE9D7','#0F0F0F','#003C7F','#BF0000','#414141','#F0DECD','#C1B3A5'
HEAD=fm.FontProperties(family=['Georgia','DejaVu Serif'],weight='normal',style='normal')
plt.rcParams.update({'font.family':['Arial','DejaVu Sans'],'font.size':12,'text.color':INK,
                     'figure.facecolor':PAPER,'axes.facecolor':PAPER,'svg.fonttype':'path'})

# Fixed path order and stopping steps, identical for every policy.
names=list('ABCDEF')
lengths=[2,6,4,2,4,2]
scalar=[];end=0
for p,n in enumerate(lengths):
    scalar.append((p,0,end,end+n));end+=n
fixed=[];fixed_end=0
for p in range(0,6,2):
    for lane in range(2):fixed.append((p+lane,lane,fixed_end,fixed_end+lengths[p+lane]))
    fixed_end+=max(lengths[p:p+2])
refill=[];ends=[0,0]
for p,n in enumerate(lengths):
    lane=min(range(2),key=lambda lane:(ends[lane],lane))
    start=ends[lane];ends[lane]+=n
    refill.append((p,lane,start,ends[lane]))
assert (end,fixed_end,max(ends))==(20,14,10)
for schedule in (scalar,fixed,refill):
    assert sorted(p for p,_,_,_ in schedule)==list(range(6))
    assert sum(e-s for _,_,s,e in schedule)==20
    for lane in (0,1):
        items=sorted((s,e) for _,l,s,e in schedule if l==lane)
        assert all(a[1]<=b[0] for a,b in zip(items,items[1:]))
# At round 3 the refilled lane reads C's first step while B reads its third.
def at(schedule,lane,round_index):
    for p,l,s,e in schedule:
        if l==lane and s<=round_index<e:return names[p]+str(round_index-s+1)
assert at(refill,0,2)=='C1' and at(refill,1,2)=='B3'

fig=plt.figure(figsize=(14,15.2))
def text(x,y,s,**kw):fig.text(x,y,s,**kw)
def rule(y):fig.add_artist(plt.Line2D([.055,.945],[y,y],transform=fig.transFigure,color=RULE,lw=.8))
def tint(color,amount):return tuple((1-amount)*np.array(to_rgb(color))+amount*np.array(to_rgb(PAPER)))

text(.055,.965,'ONCE IN A RUNTIME  /  HOW THE CODE WORKS',fontsize=11,color=BLUE,weight='bold')
text(.945,.965,'TEACHING EXAMPLE · TWO LANES',fontsize=10,ha='right',color='#5F5045')
text(.055,.914,'One instruction. Two price paths.',fontproperties=HEAD,fontsize=30)
text(.055,.875,'A path is one simulated future for a stock. A step updates its price and checks the barrier.',fontsize=13)
text(.055,.846,'SIMD lets one CPU instruction apply the same arithmetic operation to several values at once.',fontsize=13)

# Primer: vector lanes appear vertically, exactly as in the schedules below.
primer=fig.add_axes((.055,.731,.89,.090))
primer.set_xlim(0,1);primer.set_ylim(0,1);primer.axis('off')
primer.add_patch(FancyBboxPatch((0,.015),1,.97,boxstyle='round,pad=.004,rounding_size=.025',facecolor=PANEL,edgecolor='none'))
centres=[.265,.540,.815]
titles=['Prices','Next-step multipliers','Updated prices']
data=[['100','100'],['1.02','0.99'],['102','99']]
for x,title,values in zip(centres,titles,data):
    primer.text(x,.88,title,ha='center',fontsize=11,weight='bold')
    for lane,(y,value) in enumerate(zip((.49,.13),values)):
        primer.add_patch(FancyBboxPatch((x-.060,y),.12,.29,boxstyle='round,pad=.008,rounding_size=.014',facecolor=PAPER,edgecolor=RULE,lw=.65))
        primer.text(x,y+.145,value,ha='center',va='center',fontsize=17,weight='bold',color=BLUE)
primer.text(.028,.64,'Lane 1',fontsize=11,va='center',weight='bold')
primer.text(.028,.28,'Lane 2',fontsize=11,va='center',weight='bold')
primer.text(.403,.46,'×',fontsize=26,ha='center',va='center')
primer.text(.678,.46,'→',fontsize=26,ha='center',va='center')
text(.055,.708,'Each lane is a value slot inside the same vector operation. Below, follow those slots from left to right.',fontsize=11.5,color='#5F5045')

# The identical work supplied to all three approaches.
text(.055,.678,'The same six paths need different amounts of work:',fontsize=12,weight='bold')
for p,(name,n) in enumerate(zip(names,lengths)):
    x=.055+p*.148
    fig.add_artist(FancyBboxPatch((x,.631),.132,.032,boxstyle='round,pad=.003,rounding_size=.006',transform=fig.transFigure,facecolor=PANEL,edgecolor='none'))
    text(x+.012,.643,f'{name}',fontsize=13,weight='bold')
    text(x+.037,.643,f'{n} steps',fontsize=11)
text(.055,.611,'B reaches the final date (step 6). The other paths hit the barrier earlier and stop.',fontsize=11,color='#5F5045')

def schedule(ax,schedule,total,lanes,color,highlight=False):
    ax.set_xlim(-1.35,20.3);ax.set_ylim(-.48,lanes-.18)
    for lane in range(lanes):
        y=lanes-1-lane
        for r in range(total):
            ax.add_patch(Rectangle((r,y-.27),1,.54,facecolor=PANEL,edgecolor=RULE,lw=.4,hatch='////'))
        ax.text(-.30,y,'One value' if lanes==1 else f'Lane {lane+1}',ha='right',va='center',fontsize=10)
    for p,lane,start,stop in schedule:
        y=lanes-1-lane
        for t,r in enumerate(range(start,stop),1):
            ax.add_patch(Rectangle((r,y-.27),1,.54,facecolor=tint(color,.16 if p%2 else 0),edgecolor=PAPER,lw=1))
            ax.text(r+.5,y,f'{names[p]}{t}',ha='center',va='center',fontsize=9.5,weight='bold',color='white')
    if highlight:
        ax.add_patch(Rectangle((2, -.35),1,1.70,facecolor='none',edgecolor=INK,lw=1.4,zorder=8))
        ax.text(2.5,1.51,'Round 3',ha='center',fontsize=9,color=INK)
    ax.axvline(total,ymin=.04,ymax=.95,color=color,lw=1.1,ls=(0,(2,3)))
    ax.text(total+.22,(lanes-1)/2,f'{total}\nrounds',ha='left',va='center',fontsize=11,weight='bold',color=color)
    ax.axis('off')

rule(.592)
text(.055,.564,'01  Scalar: one path at a time',fontproperties=HEAD,fontsize=20,color=GRAY)
text(.055,.539,'Finish A, then B, then C. Each round updates one price.',fontsize=12)
a=fig.add_axes((.055,.487,.78,.038));schedule(a,scalar,end,1,GRAY)

rule(.467)
text(.055,.439,'02  Fixed SIMD: keep each pair together',fontproperties=HEAD,fontsize=20,color=BLUE)
text(.055,.414,'Update two prices per round. Start the next pair after both paths have finished.',fontsize=12)
a=fig.add_axes((.055,.337,.78,.061));schedule(a,fixed,fixed_end,2,BLUE)
text(.852,.372,'A stops early.\nIts slot waits\nfor B to finish.',fontsize=11,va='center',linespacing=1.5)

rule(.315)
text(.055,.287,'03  Refill SIMD: give the empty lane a new path',fontproperties=HEAD,fontsize=20,color=RED)
text(.055,.262,'When A stops, C takes its place. Both lanes keep doing useful work in this example.',fontsize=12)
a=fig.add_axes((.055,.185,.78,.061));schedule(a,refill,max(ends),2,RED,highlight=True)
text(.852,.220,'At round 3:\nlane 1 runs C1;\nlane 2 runs B3.',fontsize=11,va='center',linespacing=1.5)

text(.055,.164,'READ A BOX:',fontsize=9.5,weight='bold',color=GRAY)
text(.145,.164,'C1 = path C, its first step.',fontsize=10.5)
fig.add_artist(Rectangle((.394,.160),.024,.012,transform=fig.transFigure,facecolor=PANEL,edgecolor=RULE,hatch='////',lw=.5))
text(.431,.164,'Hatching = an inactive lane.',fontsize=10.5)
text(.055,.139,'One column is one logical loop round. In SIMD rows, the two boxes in a column advance together.',fontsize=11,weight='bold')
rule(.118)
text(.055,.091,'Fewer empty slots come with extra bookkeeping.',fontproperties=HEAD,fontsize=20)
text(.055,.066,'Refill must remember each lane’s path and date, fetch the right multiplier, and return every payoff to its original position.',fontsize=11.5)
text(.055,.049,'Once no new paths remain, refill can also leave a lane idle.',fontsize=10.5,color='#5F5045')
text(.055,.035,'Invented teaching workload: every method performs the same 20 useful price updates. Round counts are not elapsed-time measurements.',fontsize=10)
text(.055,.016,'Actual runtime also includes input access, barrier checks and bookkeeping. The benchmark tests whether refill is worth that cost.',fontsize=10)

for ext in ('png','svg'):
    fig.savefig(OUT/f'simd-mechanism-explained.{ext}',dpi=160,facecolor=PAPER)
plt.close(fig)
(OUT/'simd-mechanism-explained-data.json').write_text(json.dumps({'status':'Illustrative mechanism only; invented teaching workload','paths':dict(zip(names,lengths)),'scalar':scalar,'fixed':fixed,'refill':refill,'round_counts':{'scalar':end,'fixed':fixed_end,'refill':max(ends)},'useful_updates':20,'new_measurements':False,'checks':['Every method processes each path exactly once','Every method performs exactly 20 useful updates','Within-lane work never overlaps','Refill round 3 contains C1 and B3'],'project_source_unchanged':True},indent=2)+'\n')
print(OUT/'simd-mechanism-explained.png')
