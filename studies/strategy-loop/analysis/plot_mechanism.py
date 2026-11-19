"""Draw an account-state illustration from the reviewed static path evidence."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Polygon

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,default=ROOT/'studies/strategy-loop/results/mechanism-paths.json')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    evidence=json.loads(args.evidence.read_text())
    for row in evidence['paths']:
        expected={'read':0,'write':0} if row['order']=='strategy' else {'read':32,'write':16}
        if row['memory_operand_bytes']['state'] != expected or row['mnemonic_counts'].get('fdiv') != 1:
            raise ValueError('reviewed path no longer supports this illustration')
    style=json.loads((ROOT/'publication/visual-style.json').read_text())
    c=style['palette'];blue,red=c['blue'],c['red']
    plt.rcParams.update({'font.family':'Arial','svg.fonttype':'none'})
    fig=plt.figure(figsize=(12,10),facecolor=c['paper'])
    ax=fig.add_axes([0,0,1,1]);ax.set(xlim=(0,12),ylim=(0,10));ax.axis('off')

    def text(x,y,s,size=12,color=None,**kwargs):
        return ax.text(x,y,s,fontsize=size,color=color or c['ink'],va='center',**kwargs)

    def line(xs,ys,color=None,lw=1,**kwargs):
        ax.plot(xs,ys,color=color or c['rule'],lw=lw,**kwargs)

    def arrow(a,b,color,rad=0,lw=2,style='-|>',**kwargs):
        ax.add_patch(FancyArrowPatch(a,b,arrowstyle=style,mutation_scale=15,
                     connectionstyle=f'arc3,rad={rad}',linewidth=lw,color=color,**kwargs))

    def ledger(x,y,w,h,color,label,fields):
        # A paper account record is a metaphor for values held in registers;
        # rows are fields, not a diagram of physical register allocation.
        fold=.25
        ax.add_patch(Polygon([(x+.07,y-.07),(x+w+.07,y-.07),
                             (x+w+.07,y+h-fold-.07),(x+w-fold+.07,y+h-.07),
                             (x+.07,y+h-.07)],closed=True,facecolor=c['rule'],
                             edgecolor='none',alpha=.25))
        ax.add_patch(Polygon([(x,y),(x+w,y),(x+w,y+h-fold),
                             (x+w-fold,y+h),(x,y+h)],closed=True,
                             facecolor=c['paper'],edgecolor=color,lw=1.6))
        ax.add_patch(Polygon([(x+w-fold,y+h),(x+w-fold,y+h-fold),
                             (x+w,y+h-fold)],closed=True,facecolor=c['panel'],
                             edgecolor=color,lw=1.1))
        text(x+.19,y+h-.37,label,12,color,weight='bold')
        line([x+.17,x+w-.17],[y+h-.62]*2,color,.8)
        for i,label in enumerate(fields):
            yy=y+h-.91-i*.34
            ax.add_patch(Circle((x+.24,yy),.035,facecolor=color,edgecolor='none'))
            text(x+.39,yy,label,12,color)
            line([x+.37,x+w-.19],[yy-.15]*2,c['rule'],.55)

    def array(x,y,w,color):
        # Each row is one account. Both arrows terminate at A; after that
        # account's work, the loop advances to B and C in the stated order.
        for i,label in enumerate(('ACCOUNT A','B','C')):
            yy=y-i*.27
            hh=.46 if i==0 else .20
            ax.add_patch(FancyBboxPatch((x,yy),w,hh,
                         boxstyle='round,pad=0,rounding_size=.035',
                         facecolor=color if i==0 else c['panel'],
                         edgecolor=color if i==0 else c['rule'],lw=.9))
            text(x+w/2,yy+hh/2,label,11 if i==0 else 9,
                 c['paper'] if i==0 else c['muted'],ha='center',weight='bold')

    text(.60,9.40,'Keep the file open.',36,fontfamily='Georgia')
    text(.63,8.87,'Changing loop order changes how long an account stays in registers.',14)
    text(11.37,9.43,'ONCE IN A RUNTIME',9,c['muted'],ha='right')
    line([.63,11.37],[8.47]*2)
    line([6,6],[2.0,8.05])

    text(.70,8.08,'STRATEGY-FIRST',11,blue,weight='bold')
    text(.70,7.56,'One account. Many bars.',23,blue,fontfamily='Georgia')
    text(6.70,8.08,'EVENT-FIRST',11,red,weight='bold')
    text(6.70,7.56,'One bar. Many accounts.',23,red,fontfamily='Georgia')

    # The blue record stays in place while the clock advances beside it.
    ax.add_patch(Circle((2.55,5.38),1.72,facecolor=c['panel'],edgecolor='none'))
    text(2.61,6.92,'HELD IN REGISTERS',10,blue,ha='center',weight='bold')
    ledger(1.34,4.16,2.5,2.43,blue,'ACCOUNT A',
           ('cash & shares','peak & drawdown','fees, notional, trades'))
    text(4.90,6.92,'BAR',10,c['muted'],ha='center')
    line([4.90]*2,[4.04,6.45],blue,2)
    for yy,label in ((6.23,'t'),(5.40,'t+1'),(4.57,'t+2')):
        ax.add_patch(Circle((4.90,yy),.265,facecolor=blue,edgecolor=c['paper'],lw=3))
        text(4.90,yy,label,11,c['paper'],ha='center')
        line([3.88,4.52],[yy]*2,blue,1.1,linestyle=(0,(2,3)))
    arrow((4.90,4.10),(4.90,3.77),blue,lw=1.7)
    text(4.90,3.53,'…',20,blue,ha='center')
    text(2.59,3.84,'same account, next bar',12,blue,ha='center')
    array(1.05,2.86,3.12,blue)
    text(2.61,3.49,'ACCOUNT ARRAY',9,c['muted'],ha='center')
    arrow((1.19,3.37),(1.19,4.35),c['muted'],rad=-.50,lw=1.2)
    arrow((3.99,4.35),(3.99,3.37),c['muted'],rad=-.50,lw=1.2)
    text(.71,3.78,'load\nonce',10,c['muted'],ha='center',linespacing=1.3)
    text(4.39,3.01,'store after\nthe history',10,c['muted'],linespacing=1.3)
    text(.80,1.99,'0 B',29,blue,fontfamily='Georgia')
    text(2.09,1.99,'of account loads/stores\ninside a reviewed steady update',12,blue,linespacing=1.35)

    # The red account record is revisited through the array on each update.
    ax.add_patch(Circle((9.02,5.38),1.72,facecolor=c['panel'],edgecolor='none'))
    text(9.02,6.92,'CURRENT ACCOUNT IN REGISTERS',10,red,ha='center',weight='bold')
    ledger(7.91,4.43,2.22,2.16,red,'ACCOUNT A',
           ('cash & shares','peak & drawdown'))
    array(7.48,2.86,3.12,red)
    text(9.04,3.49,'ACCOUNT ARRAY',9,c['muted'],ha='center')
    arrow((7.88,3.40),(7.78,5.30),red,rad=-.90,lw=3)
    arrow((10.25,5.30),(9.82,3.40),red,rad=-.80,lw=3)
    text(6.96,4.33,'32 B',22,red,fontfamily='Georgia',ha='center',
         bbox=dict(facecolor=c['paper'],edgecolor='none',pad=3))
    text(6.96,3.97,'read',11,red,ha='center',
         bbox=dict(facecolor=c['paper'],edgecolor='none',pad=2))
    text(11.10,4.33,'16 B',22,red,fontfamily='Georgia',ha='center',
         bbox=dict(facecolor=c['paper'],edgecolor='none',pad=3))
    text(11.10,3.97,'write',11,red,ha='center',
         bbox=dict(facecolor=c['paper'],edgecolor='none',pad=2))
    text(9.02,4.72,'equity · peak · drawdown',10,red,ha='center')
    text(9.02,1.99,'A → B → C → … then the next bar',13,red,ha='center')

    line([.63,11.37],[1.59]*2)
    text(.65,1.18,'Even with no trade, both loops still mark equity and update peak / drawdown.',13)
    text(.65,.73,'GCC 16.2 / AArch64 · Reviewed steady cash/long paths · Both feature layouts',10,c['muted'])
    text(.65,.40,'Bytes count account-field load/store operands; caches may serve them. Diagram is schematic.',10,c['muted'])
    args.output.mkdir(parents=True,exist_ok=True)
    for extension in ('png','svg'):
        fig.savefig(args.output/('09-account-state-mechanism.'+extension),dpi=180,facecolor=c['paper'])
    plt.close(fig)
    metadata=dict(kind='static mechanism illustration',visual_metaphor='keep one account file open versus revisit the account array',evidence_sha256=hashlib.sha256(args.evidence.read_bytes()).hexdigest(),
                  generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),style=style['id'])
    (args.output/'mechanism-figure.json').write_text(json.dumps(metadata,indent=2)+'\n')


if __name__=='__main__':
    main()
