#!/usr/bin/env python3
"""Optional visual output for ECON-05 (requires matplotlib). Numeric core is stdlib."""
import csv
from decimal import Decimal as D
from pathlib import Path
import matplotlib.pyplot as plt
BASE=Path(__file__).resolve().parent
with (BASE/'results'/'econ05_sweep_30rows.csv').open(newline='',encoding='utf-8') as f:
    data=list(csv.DictReader(f))

plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"axes.titlesize":15,"axes.labelsize":10,"savefig.dpi":190})
A=[0,.25,.5,.75,1.0]
COL={1:'#4E79A7',10:'#E09F3E',100:'#25876C'}

def series(n,price,key):
    return [float(next(r[key] for r in data if int(r['activity_deposits_per_user_90d'])==n and r['fee_scenario']==price and D(r['user_share_alpha'])==D(str(a)))) for a in A]

# 1. Conditional network-payment difference; NOT WTP or an empirically measured privacy premium.
fig,ax=plt.subplots(figsize=(8.8,5.25))
for n in [1,10,100]:
    ax.plot([a*100 for a in A],series(n,'p50','user_pool_difference_vs_B0_eur_user'),marker='o',lw=2.7,label=f'{n} deposits',color=COL[n])
ax.axhline(0,color='#4B5563',lw=1.2,linestyle='--')
ax.set(title='Conditional ZK–signed network payment difference (B0)',xlabel='User-funded share of incremental ZK pool (%)',ylabel='EUR per user / 90 days — conditional net')
ax.set_xticks([0,25,50,75,100]);ax.grid(axis='y',alpha=.22);ax.legend(title='Activity',frameon=False,loc='upper left')
ax.text(.01,-.21,'Negative: ZK has lower conditional net network cost than signed.\nExcludes unknown user expenses, time and actual reimbursement feasibility.',transform=ax.transAxes,fontsize=9,color='#374151')
fig.subplots_adjust(bottom=.29,top=.88,left=.115,right=.96)
fig.savefig(BASE/'figures'/'figure_1_conditional_network_payment_difference_p50.png',bbox_inches='tight');plt.close(fig)

# 2. Service budget for modeled population, p50.
fig,ax=plt.subplots(figsize=(8.8,5.25))
for n in [1,10,100]:
    ax.plot([a*100 for a in A],series(n,'p50','service_subsidy_eur_population'),marker='o',lw=2.7,label=f'{n} deposits',color=COL[n])
ax.set(title='Conditional service reimbursements for 1,000 modeled users — p50',xlabel='User-funded share of ZK access pool (%)',ylabel='EUR / 90 days for N=1,000')
ax.set_xticks([0,25,50,75,100]);ax.set_ylim(bottom=0);ax.grid(axis='y',alpha=.22);ax.legend(title='Activity',frameon=False,loc='upper right')
ax.text(.01,-.19,'Measured gas component only; excludes provider, settlement and fixed costs.\n100% user share implies no service reimbursement, not zero other service cost.',transform=ax.transAxes,fontsize=9,color='#374151')
fig.subplots_adjust(bottom=.26,top=.88,left=.11,right=.97)
fig.savefig(BASE/'figures'/'figure_2_service_reimbursement_p50_N1000.png',bbox_inches='tight');plt.close(fig)

# 3. Same activity and payment policy repriced at p90; not a traffic or delay scenario.
fig,ax=plt.subplots(figsize=(8.8,5.25))
for n in [1,10,100]:
    ax.plot([a*100 for a in A],series(n,'p90','service_subsidy_eur_population'),marker='o',lw=2.7,label=f'{n} deposits',color=COL[n])
ax.set(title='Same service reimbursements repriced at archived p90',xlabel='User-funded share of ZK access pool (%)',ylabel='EUR / 90 days for N=1,000')
ax.set_xticks([0,25,50,75,100]);ax.set_ylim(bottom=0);ax.grid(axis='y',alpha=.22);ax.legend(title='Activity',frameon=False,loc='upper right')
ax.text(.01,-.19,'Gas counts unchanged; only the archived price changes (p90 ≈ 5.48 × p50).\nThis is not a stress test of user timing, network congestion or reimbursement implementation.',transform=ax.transAxes,fontsize=9,color='#374151')
fig.subplots_adjust(bottom=.26,top=.88,left=.11,right=.97)
fig.savefig(BASE/'figures'/'figure_3_service_reimbursement_p90_N1000.png',bbox_inches='tight');plt.close(fig)
print('Saved 3 reproducible research figures to figures/')
