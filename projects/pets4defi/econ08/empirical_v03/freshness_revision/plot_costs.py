"""Regenerate the paper figure from paired fixed-freshness economic summaries."""
import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE=Path(__file__).resolve().parent
def draw():
    with (HERE/'results/subdaily_summary.csv').open() as f:
        rows=[r for r in csv.DictReader(f) if r['issuers']=='16' and r['access_model']=='session']
    styles=[('selective',1,'Selective','#142b4a','s'),('group_like_rate',2,'Like rate, G=2','#077d68','o'),
            ('group_like_rate',4,'Like rate, G=4','#077d68','^'),('group_like_rate',8,'Like rate, G=8','#077d68','D'),
            ('group_random',2,'Random, G=2','#d58417','o'),('group_random',4,'Random, G=4','#d58417','^'),
            ('group_random',8,'Random, G=8','#d58417','D'),('cover_0.5',1,'Cover, ρ=0.5','#784b98','x'),
            ('common',16,'Common','#41649b','P'),('batch',16,'Batch / independent heartbeats','#10191e','+')]
    with plt.rc_context({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42}):
        fig,axes=plt.subplots(1,3,figsize=(13,5.2),sharex=True,sharey=True)
        for ax,period,tag in zip(axes,(3300,21300,86100),('1 hour','6 hours','24 hours')):
            relevant=[r for r in rows if int(r['period_s'])==period]
            for policy,g,lab,color,mark in styles:
                r=next(r for r in relevant if r['policy']==policy and int(r['group_size'])==g)
                ax.errorbar(float(r['full']),100*float(r['switch_disagreement']),xerr=float(r['full_ci95_halfwidth']),
                            yerr=100*float(r['disagreement_ci95_halfwidth']),fmt=mark,color=color,ms=8,
                            mew=1.6,elinewidth=.9,capsize=2,fillstyle='none' if mark in ['o','^','D'] else 'full')
            ax.set_title('Freshness limit '+tag,fontsize=13);ax.grid(alpha=.18);ax.set_axisbelow(True)
            ax.set_xlabel('Full proofs per holder in 90 days')
        axes[0].set_ylabel('Accesses where a change of issuer\nchanges the proof decision (%)')
        axes[0].set_ylim(-1.5,32);axes[0].set_xlim(14.3,29)
        handles=[Line2D([],[],color=c,marker=m,linestyle='none',markersize=7,label=lab,
                         fillstyle='none' if m in ['o','^','D'] else 'full') for _,_,lab,c,m in styles]
        fig.legend(handles=handles,loc='lower center',ncol=5,frameon=False,fontsize=9,bbox_to_anchor=(.51,-.006))
        fig.suptitle('Cache response at a matched revocation deadline',fontsize=17,y=.99)
        fig.text(.507,.907,'16 synthetic issuers from two Base templates  |  paired 20-minute sessions  |  20 seeds  |  assumed lag 5 min',ha='center',color='#475466')
        fig.subplots_adjust(left=.082,right=.99,top=.79,bottom=.235,wspace=.12)
        target=HERE.parent/'figures';target.mkdir(exist_ok=True)
        for fmt in ('png','pdf'):
            fig.savefig(target/('cost_observability.'+fmt),dpi=170,bbox_inches='tight')
        plt.close(fig)
if __name__=='__main__':draw()
