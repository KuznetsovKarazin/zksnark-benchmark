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

# The dated matched-SLA experiment supplies the cost panel.
import runpy
runpy.run_path(str(root/'freshness_revision'/'plot_costs.py'),run_name='__main__')

columns=sorted({k for row in rows for k in row})
with (root/'results/stress/summary.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(rows)
print(json.dumps({'figures':4,'summary_rows':len(rows)}))
