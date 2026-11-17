#!/usr/bin/env python3
"""Figures from saved seed-level experiments; no fabricated or extrapolated cells."""
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root=Path(__file__).parents[1]
rows=json.loads((root/'results/stress/summary.json').read_text())
out=root/'figures';out.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180})
fig,axes=plt.subplots(1,2,figsize=(10,3.9),layout='constrained')
for ax,b in zip(axes,[4,64]):
    values=np.array([[next(r['accuracy'] for r in rows if r['case']<60 and r['issuers']==b and r['label_error']==e and r['missing']==m) for e in [0,.05,.1,.2]] for m in [0,.1,.3]])*100
    im=ax.imshow(values,vmin=0,vmax=100,cmap='viridis',aspect='auto')
    for i in range(3):
        for j in range(4):ax.text(j,i,f'{values[i,j]:.1f}%',ha='center',va='center',color='white' if values[i,j]<65 else 'black',fontsize=11)
    ax.set_xticks(range(4),['0%','5%','10%','20%']);ax.set_yticks(range(3),['0%','10%','30%'])
    ax.set_xlabel('Full/hit label error');ax.set_ylabel('Missing accesses')
    ax.set_title(f'{b} issuers; prior-only {100/b:.2f}%')
fig.suptitle('Issuer identification after 90 days — exact daily-model HMM',fontsize=14)
fig.colorbar(im,ax=axes,label='Accuracy (%)',shrink=.8)
fig.savefig(out/'hmm_robustness.png');fig.savefig(out/'hmm_robustness.pdf');plt.close(fig)

fig,ax=plt.subplots(figsize=(8,4.5),layout='constrained')
for policy,label,color in [('selective','Selective','#bd4b38'),('cover','Cover (rho = 0.5)','#a06a00'),('common','Common, each update','#3a5894'),('batch','Common, 7-day batch','#147d66')]:
    row=next(r for r in rows if r['case']<78 and r['issuers']==4 and r['policy']==policy and r['label_error']==.1 and r['missing']==.3)
    ax.errorbar(row['full_per_holder'],row['accuracy']*100,xerr=row['full_per_holder_ci95_halfwidth'],yerr=row['accuracy_ci95_halfwidth']*100,fmt='o',color=color,capsize=4,markersize=8)
    offset=(8,8) if policy!='batch' else (8,-20)
    ax.annotate(label,(row['full_per_holder'],row['accuracy']*100),textcoords='offset points',xytext=offset,color=color)
ax.axhline(25,color='gray',ls='--',lw=1,label='Uniform-prior baseline')
ax.set(xlabel='Full authorizations per holder / 90 days',ylabel='Issuer identification accuracy (%)',ylim=(15,105),xlim=(8,31))
ax.set_title('Cost proxy versus observability: batching trades freshness\n4 issuers, 10% label error, 30% missing; 20 seeds')
ax.legend(loc='upper right');fig.savefig(out/'cost_observability.png');fig.savefig(out/'cost_observability.pdf');plt.close(fig)

columns=sorted({k for row in rows for k in row})
with (root/'results/stress/summary.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(rows)
(out/'CAPTIONS.md').write_text('''# Figure interpretation

Both figures use the 80-case synthetic daily model (128 holders per run, 20
independent seeds). Noise parameters and activity probability are known to the
attacker. Rates differ across issuers; the displayed panels use uniform issuer
priors and issuer-independent access probabilities. Errors are independent.
These are not real-chain identification rates.

`hmm_robustness`: all displayed cells were run; color and labels give final-day
accuracy. Seed-level Student-t 95% intervals are in `summary.csv`. Identification
with posterior >= 0.95 is a different metric, available in the result files.

`cost_observability`: error bars are 95% intervals across seed means. The x-axis
is a proof-count cost proxy, not money or measured L2 fees. A seven-day batching
period additionally needs ingestion/publication/finality lag L in its freshness
budget. Common/batch preserve the prior in this channel; this does not prove
privacy against auxiliary information, address linkage or service-side signals.
''')
print(json.dumps({'figures':4,'summary_rows':len(rows)}))
