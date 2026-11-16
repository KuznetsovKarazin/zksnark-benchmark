import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
def read(name):return list(csv.DictReader((ROOT/'results'/name).open()))
def save(fig,name):
    fig.savefig(ROOT/'figures'/f'{name}.png',dpi=190,bbox_inches='tight')
    fig.savefig(ROOT/'figures'/f'{name}.svg',bbox_inches='tight')
    plt.close(fig)

plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                     'axes.grid':True,'grid.alpha':.2,'svg.fonttype':'none'})
rows=read('weekly_one_coin_exact.csv')
fig,axes=plt.subplots(1,2,figsize=(10,3.7),layout='constrained')
x=[float(r['gas_proxy'])/1e6 for r in rows]
for ax,key,label in [(axes[0],'entropy_bits','Remaining entropy (bits)'),
                     (axes[1],'singleton_probability','Exact identification probability (%)')]:
    scale=100 if key=='singleton_probability' else 1
    y=[float(r[key])*scale for r in rows]
    ax.plot(x,y,color='#14629b',lw=2)
    for rho in [0,.25,.5,.75,.95,1]:
        r=next(r for r in rows if float(r['rho'])==rho)
        xx=float(r['gas_proxy'])/1e6;yy=float(r[key])*scale
        ax.scatter([xx],[yy],color='#14629b',s=22)
        if rho in [.25,.75,.95]:ax.annotate(str(rho),(xx,yy),xytext=(-20,8),textcoords='offset points',fontsize=9)
    ax.set_xlabel('Modeled access gas per holder (millions)');ax.set_ylabel(label)
    ax.set_xlim(7.9,10.8)
fig.suptitle('One coin per publication — exact weekly expectations; labels show ρ',fontsize=11)
save(fig,'01_one_coin_frontier')

rows=read('clustering_summary.csv')
fig,ax=plt.subplots(figsize=(9,3.8),layout='constrained')
names=['selective','coin_0.25','coin_0.75','coin_0.95','common'];xs=[0,.25,.75,.95,1]
for accesses,color,marker in [('30','#b54c35','s'),('100','#14629b','o'),('400','#37834e','^')]:
    selected=[next(r for r in rows if r['holders_per_issuer']=='8' and r['accesses']==accesses and r['nu']=='12' and r['policy']==name) for name in names]
    ax.errorbar(xs,[float(r['ari_mean']) for r in selected],yerr=[float(r['ari_sd']) for r in selected],
        color=color,marker=marker,capsize=3,lw=1.7,label=accesses+' accesses / holder')
ax.axhline(0,color='#555',lw=.7);ax.set_ylim(-.12,1.12);ax.set_xlim(-.03,1.03)
ax.set_xlabel('Foreign-publication cover probability ρ (0 selective, 1 common)')
ax.set_ylabel('Clustering adjusted Rand index')
ax.legend(loc='upper right',fontsize=9)
ax.set_title('Anonymous publications, 32 holders, 12 expected updates per issuer\nMeans ± sample SD over 20 seeds; one fixed baseline attacker',fontsize=11)
save(fig,'02_anonymous_clustering')

rows=read('outage_summary.csv')
fig,axes=plt.subplots(2,2,figsize=(9,5.5),sharex=True,sharey=True,layout='constrained')
policies=[('common','Common','#b54c35'),('fresh_k','Current fresh-k','#14629b'),('guard_k','History guard','#37834e')]
for ax,(fail,rec) in zip(axes.flat,[('0.02','0.2'),('0.02','0.5'),('0.1','0.2'),('0.1','0.5')]):
    for policy,label,color in policies:
        sub=[next(r for r in rows if r['issuers']=='4' and r['k']=='2' and r['fail']==fail and r['recovery']==rec and r['freshness_days']==str(f) and r['policy']==policy) for f in [1,3,7]]
        ax.plot([1,3,7],[float(r['availability_mean'])*100 for r in sub],'-o',color=color,label=label)
    ax.set_title(f'Failure {fail}/day; recovery {rec}/day',fontsize=10)
    ax.set_xticks([1,3,7]);ax.set_ylim(0,103)
for ax in axes[-1]:ax.set_xlabel('Freshness cap (days)')
for ax in axes[:,0]:ax.set_ylabel('Accepted scheduled requests (%)')
handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside upper center',ncol=3,frameon=False)
save(fig,'03_availability_grid')

rows=read('compensation_reference.csv')
fig,ax=plt.subplots(figsize=(8.5,3.7),layout='constrained')
for rule,label,offset,color in [('publication_frequency','Publication frequency',-.18,'#14629b'),('shapley_externality','Shapley marginal cost',.18,'#b54c35')]:
    values=[sum(float(r['reimbursement_gas_equivalent']) for r in rows if r['case']=='asymmetric_A32' and r['rule']==rule and r['paying_issuer']==str(i))/1e6 for i in range(1,5)]
    ax.bar([i+offset for i in range(1,5)],values,.34,label=label,color=color)
ax.set_xticks(range(1,5),[f'Issuer {i}' for i in range(1,5)])
ax.set_ylabel('Allocated compensation (million gas equivalent)')
ax.set_title('Asymmetric 32-holder model — same total externality, different incidence',fontsize=11)
ax.legend(frameon=False,loc='upper left');save(fig,'04_compensation')
print('Four figures created in PNG and SVG')
