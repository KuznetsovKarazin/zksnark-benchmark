#!/usr/bin/env python3
"""Build Nataliya's small reading packet from validated follow-up results."""
import csv,json,shutil,hashlib,zipfile
from decimal import Decimal as D
from pathlib import Path
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

P=Path(__file__).resolve().parent
PACK=P/'handoff';PACK.mkdir(exist_ok=True)
F=D('0.130658648')*D('1e-9')*D('2164.73')
rows=list(csv.DictReader((P/'archived_refill_controls.csv').open()))
selected=[r for r in rows if r['refill']=='daily' and r['phase_s']=='0' and r['stage']=='continuing_after_1d' and r['mechanism'].startswith('zk')]
lookup={(r['mechanism'],r['updates'],r['stage']):r for r in rows if r['refill']=='daily' and r['phase_s']=='0'}
def csvwrite(path,rr):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)
small=[]
for r in selected:
    full=lookup[r['mechanism'],r['updates'],'full_lifecycle']
    small.append({'B':r['mechanism'][-1],'updates':r['updates'],'holders':4,'startup_expense_gas':int(full['holder_C'])-int(r['holder_C']),
        'service_expense_gas':int(r['holder_C']),'service_pool_K_gas':int(r['pool_K']),'service_SELF_sum_K_gas':int(r['SELF_sum_K']),
        'pool_K_eur_q0':str(D(r['pool_K'])*F),'SELF_sum_K_eur_q0':str(D(r['SELF_sum_K'])*F),
        'scope':'day1 onward; original daily clock; startup separately funded; no AA overhead'})
csvwrite(PACK/'OPERATING_CASES.csv',small)
sensitivity=[]
for r in small:
    for multiplier in [1,10,100,1000]:
        sensitivity.append({'B':r['B'],'updates':r['updates'],'holders':4,'price_multiplier':multiplier,
            'gas_price_gwei':str(D('0.130658648')*multiplier),'ETH_EUR':2164.73,
            'pool_K_eur':str(D(r['service_pool_K_gas'])*F*multiplier),'SELF_sum_K_eur':str(D(r['service_SELF_sum_K_gas'])*F*multiplier),
            'pooling_reduction_eur':str(D(r['service_SELF_sum_K_gas']-r['service_pool_K_gas'])*F*multiplier),
            'scope':'price sensitivity only; fixed gas and instantaneous costless refills'})
csvwrite(PACK/'PRICE_SENSITIVITY.csv',sensitivity)
shutil.copy2(P/'K05_K06_crosswalk.csv',PACK/'K05_K06_crosswalk.csv')
shutil.copy2(P/'model_summary.csv',PACK/'MODEL_SUMMARY.csv')
for source,dest in [('fee_components.csv','OP_FEE_COMPONENTS.csv'),('funding_summary.csv','OP_FUNDING_SUMMARY.csv')]:
    shutil.copy2(P/'op_projection'/source,PACK/dest)

fig,axes=plt.subplots(1,2,figsize=(10,3.3),sharey=True)
for ax,stage,title in zip(axes,['full_lifecycle','continuing_after_1d'],['One reserve from startup','Operating reserve after day 1']):
    for d,update,label,color in [(-.19,'control','No updates','#687b8b'),(.19,'weekly','Weekly updates','#176b78')]:
        vals=[int(lookup[f'zk_B{b}',update,stage]['pool_K'])/1e6 for b in [1,2,4]]
        ax.bar([i+d for i in range(3)],vals,width=.36,label=label,color=color)
    ax.set_xticks(range(3),['B1','B2','B4']);ax.set_title(title);ax.spines[['right','top']].set_visible(False)
    ax.set_ylim(0,2.65);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
axes[0].set_ylabel('Holder pool K in million gas');axes[1].legend(frameon=False,fontsize=9,loc='upper right')
fig.suptitle('Same archived workload, different funding policies',fontsize=13)
fig.text(.5,.01,'N16, A4, HIGH, zero grace, 30d TTL, daily refills. Startup remains a separate expense in the right panel.',ha='center',fontsize=8)
fig.tight_layout(rect=[0,.04,1,.95]);fig.savefig(PACK/'RESERVE_COMPARISON.png',dpi=190);plt.close(fig)

doc=Document();sec=doc.sections[0];sec.page_width=Inches(8.5);sec.page_height=Inches(11)
sec.top_margin=sec.bottom_margin=Inches(.65);sec.left_margin=sec.right_margin=Inches(.75)
for name in ['Normal','Title','Subtitle','Heading 1','Heading 2']:
    st=doc.styles[name];st.font.name='Calibri';st.font.color.rgb=RGBColor(0,0,0)
doc.styles['Normal'].font.size=Pt(11);doc.styles['Normal'].paragraph_format.space_after=Pt(6)
doc.styles['Normal'].paragraph_format.line_spacing=1.05
doc.styles['Title'].font.size=Pt(20);doc.styles['Heading 1'].font.size=Pt(13)
doc.core_properties.author='Oleksandr Kuznetsov'
doc.add_paragraph('ECON 08 Technical Follow Up',style='Title')
doc.add_paragraph('For Nataliya Kolyada  |  Version 0.5  |  15 November 2026',style='Subtitle')
doc.add_paragraph('Thank you for completing the first economic checkpoint. I have supplied the missing common-cost baseline and checked the timing model. Your original totals remain valid. The next task is a short economic addendum using the small tables in this package.')
doc.add_heading('How this extends our previous work',level=1)
doc.add_paragraph('PUB-01 explains why revocations create additional authorizations and gas costs. ECON-07 identifies the expenses and who pays them. ECON-08 asks how much money must be available between account refills. A higher total expense does not necessarily mean a higher peak reserve.')
doc.add_heading('The technical question is resolved',level=1)
doc.add_paragraph('The four approvals are token allowances, a common K05 expense. Three new unchecked-deposit runs, with 1,200 deposits, provide the missing baseline. For the four-holder B2 case over 90 days:')
table=doc.add_table(rows=1,cols=3);table.autofit=False
for c,w in zip(table.columns,[3.15,1.8,1.8]):c.width=Inches(w)
for c,t in zip(table.rows[0].cells,['Gas component','Weekly updates','No updates']):c.text=t
for vals in [('K05 common deposit and allowance','22,226,604','22,226,604'),('K06 incremental eligibility','13,494,056','8,872,428'),('Total holder gas','35,720,660','31,099,032')]:
    for c,t in zip(table.add_row().cells,vals):c.text=t
for i,row in enumerate(table.rows):
    for c in row.cells:
        c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
        pr=c._tc.get_or_add_tcPr();b=OxmlElement('w:tcBorders')
        for edge in ['top','bottom','left','right']:
            el=OxmlElement('w:'+edge);el.set(qn('w:val'),'single');el.set(qn('w:sz'),'4');el.set(qn('w:color'),'D9D9D9');b.append(el)
        pr.append(b)
        if i==0:
            sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'E5EDF2');pr.append(sh)
        for p in c.paragraphs:
            p.paragraph_format.space_before=Pt(5);p.paragraph_format.space_after=Pt(5)
            for run in p.runs:run.font.size=Pt(10);run.bold=(i==0)
doc.add_paragraph('K05 includes the original approval gas plus the new unchecked access subtotal. K06 is the remainder; do not add full transaction gas again. Shared deployment and publication expenses stay separate.',style='Normal')
doc.add_heading('The primary hypothesis is still unconfirmed',level=1)
doc.add_paragraph('The independent recurrence matches all 8,832 ordinary accesses in 54 archived scenarios exactly. The bounded model covers 960 workloads. Across all 360 ZK update/control pairs, daily and weekly full-lifecycle targets remain unchanged under common gas coefficients: startup determines the peak. This does not justify a broad new EVM campaign.')
doc.add_picture(str(PACK/'RESERVE_COMPARISON.png'),width=Inches(6.8))
doc.add_page_break()
doc.add_heading('A separate operating policy has a different result',level=1)
doc.add_paragraph('If startup is funded separately, continuing service begins after day 1 on the same refill calendar. In the archived daily case, weekly revocations increase the B1 pool target by 281,676 gas, but reduce it by 294,650 gas for B2 and 582,789 gas for B4. Renewals move between days and can become less synchronized. Startup expenses still have to be paid.')
doc.add_paragraph('For B2 with weekly updates, the continuing-service pool needs 1,117,194 gas-equivalent, versus 1,558,300 for the sum of separate holder targets. The reduction is about 28.3%, but only EUR 0.124763 for four holders at the historical reference price. This is a reduction in operating balances, not in gas expense. The revised policy needs economic justification and scientific review.')
doc.add_heading('What I ask you to return',level=1)
for text in [
    'Save a new revision of your note with the supplied K05/K06 crosswalk. Keep accepted ECON-07 and the original v0.2.4 submission unchanged.',
    'Explain separately the full-lifecycle result and the policy that funds startup separately. Identify the sources of startup capital, operating balances and later top-ups; retained balances remain assets.',
    'Use OPERATING_CASES.csv and PRICE_SENSITIVITY.csv to discuss absolute and relative scale. Explain whether the operating-policy extension is economically meaningful. Do not invent a holder budget or willingness to pay.',
    'Use the OP fee scenario only within its stated assumptions. Flag missing paymaster validation/bundling costs, refill costs or delay, and off-chain issuance/KYC inputs. These remain distinct from the supplied direct-transaction figures.'
]:doc.add_paragraph(text,style='List Number')
doc.add_paragraph('Please return one short addendum of about 1–2 pages and any amended tables. Soft target: 23 November, adjustable together, before our 25 November planning meeting. No software installation, cryptographic review, new experiments or full manuscript is needed.')
doc.add_heading('Files and boundaries',level=1)
doc.add_paragraph('Start with this note and the three small CSV files: K05_K06_crosswalk, OPERATING_CASES and PRICE_SENSITIVITY. MODEL_SUMMARY reports the full sensitivity counts; OP_FEE_NOTE explains the L2 projection. The technical README, source code, raw receipts and complete model grid are for information only and are linked from the repository.')
doc.add_paragraph('Historical price: 0.130658648 gwei and EUR 2,164.73 per ETH, observed on 20 October 2026. Price multiples are scenarios. All reserve estimates are hindsight actual-debit floors; they are not safe paymaster deposits. Delta above one day and alternative TTL values are model-only. A32, stochastic tails and large-population scaling remain deferred.')
doc.add_paragraph('Oleksandr owns the technical inputs, research scope and decision on a new article. The immediate purpose of your addendum is to interpret these findings and identify the economic conditions that would make the next step worthwhile.')
doc.save(PACK/'START_HERE_v05.docx')
print(str(PACK/'START_HERE_v05.docx'))
