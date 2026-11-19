"""Six-page reviewer note. Numerical results are read from the reproducible CSVs."""
import csv
import json
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT

ROOT=Path(__file__).resolve().parents[1]
def read(name):return list(csv.DictReader((ROOT/'results'/name).open()))
V=json.loads((ROOT/'results/validation.json').read_text())
weekly=read('weekly_one_coin_exact.csv')
cluster=read('clustering_summary.csv')
doc=Document();sec=doc.sections[0]
sec.page_width=Cm(21);sec.page_height=Cm(29.7)
sec.top_margin=Cm(1.7);sec.bottom_margin=Cm(1.7);sec.left_margin=Cm(2);sec.right_margin=Cm(2)
normal=doc.styles['Normal'];normal.font.name='Arial';normal.font.size=Pt(10.5)
normal.paragraph_format.space_after=Pt(6);normal.paragraph_format.line_spacing=1.05
for name,size in [('Title',22),('Heading 1',16),('Heading 2',12)]:
    style=doc.styles[name];style.font.name='Arial';style.font.size=Pt(size)
    style.font.color.rgb=RGBColor(0,0,0)
    style.paragraph_format.space_before=Pt(8);style.paragraph_format.space_after=Pt(7)
doc.core_properties.title='The cost of hiding the issuer'
doc.core_properties.subject='ECON08 observability pilot v0.2; research review'
doc.core_properties.author='Oleksandr Kuznetsov'
footer=sec.footer.paragraphs[0];footer.alignment=2
run=footer.add_run('ECON08 · v0.2  |  ');run.font.size=Pt(8)
field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)

def p(text,bold=False):
    x=doc.add_paragraph();x.add_run(text).bold=bold;return x
def page(title):doc.add_page_break();doc.add_heading(title,1)
def table(headers,rows,widths):
    t=doc.add_table(rows=1,cols=len(headers));t.style='Table Grid';t.autofit=False
    t.alignment=WD_TABLE_ALIGNMENT.CENTER
    for col,w in zip(t.columns,widths):col.width=Cm(w)
    borders=OxmlElement('w:tblBorders')
    for edge in ['top','left','bottom','right','insideH','insideV']:
        e=OxmlElement('w:'+edge);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');borders.append(e)
    t._tbl.tblPr.append(borders)
    for cell,text,w in zip(t.rows[0].cells,headers,widths):
        cell.width=Cm(w);cell.text=text
        for r in cell.paragraphs[0].runs:r.bold=True
        sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'E9EDF1');cell._tc.get_or_add_tcPr().append(sh)
    head=OxmlElement('w:tblHeader');t.rows[0]._tr.get_or_add_trPr().append(head)
    for row in rows:
        for cell,text,w in zip(t.add_row().cells,row,widths):cell.width=Cm(w);cell.text=str(text)
    for row in t.rows:
        split=OxmlElement('w:cantSplit');row._tr.get_or_add_trPr().append(split)
        for cell in row.cells:
            cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            for pa in cell.paragraphs:
                pa.paragraph_format.space_before=Pt(3);pa.paragraph_format.space_after=Pt(3)
                for r in pa.runs:r.font.size=Pt(9)
    return t
def fig(name,caption,width=17):
    doc.add_picture(str(ROOT/'figures'/name),width=Cm(width))
    x=p(caption)
    for r in x.runs:r.font.size=Pt(9)

doc.add_heading('The cost of hiding the issuer',0)
p('Conditional bounds and modeled access costs | ECON08 v0.2 | 16 November 2026')
p('Result',True)
p('The bounded follow-up is justified. In the specified observable-cache architecture, common invalidation minimizes the number of full authorizations under perfect issuer hiding. The pilot quantifies this requirement and the cost savings obtained by relaxing hiding. This is an architectural result, not a universal theorem about credential systems. A distinct scientific contribution still requires independent review.')
table(['Component','Evidence'],[
 ['Common invalidation','Scoped necessity and authorization-count optimality proofs; exhaustive checks on 576 small schedules.'],
 ['One coin per publication','Exact weekly curve at 21 rho values. Savings against common invalidation: 6.11% at rho=0.75 and 1.22% at rho=0.95.'],
 ['Anonymous publications','1,800 clustering runs with 16/32/64 holders; separate correct and false attribution after an external anchor.'],
 ['Availability','Full outage and freshness grid; the two-branch support condition is a supporting partition lemma.'],
 ['Economic incidence','Three cases, 96 coalition costs, two issuer-funded allocations and an equal-per-holder beneficiary benchmark.']],[4.3,12.7])
p('Validation scope',True)
p('All 8,832 access decisions in 54 archived scenarios match the replay. The modeled grids contain 78,168 runs and 25,246,120 decisions. Exact enumerations supplement these runs. The original 34 unit tests are retained; four beneficiary-accounting tests bring the total to 38. The reproduction command reruns the calculations and compares numeric files byte for byte. This is internal validation, not external replication.')
p('No new EVM measurements were made. All new policies use the same archived B1 gas coefficients: 464,200 for first access, 67,610 for a cache hit and 355,749 for reauthorization. No new contract or private selective-cache implementation is supplied.')
p('Interpretation',True)
p('One-coin cover gives real cost savings, but ln(1/rho) is not a privacy bound for the full observation. Clustering anonymous histories does not automatically name their issuers. Failure of one attack algorithm is not evidence of security against stronger observers.')

page('What the conditional results establish')
p('Model assumptions',True)
p('There is one fixed hidden issuer, a fixed sequence of successful accesses and public issuer-labeled publications. The observer links accesses and distinguishes full authorization from a cache hit. A full authorization resets TTL and absorbs earlier publications. A hit does not independently verify current status. After an own-issuer publication and the expiry of grace delta, the architecture requires a full authorization. Grace is not a batching interval.')
p('Necessary common invalidation',True)
p('Once a publication makes a hit invalid for issuer j, safety requires a full authorization under that issuer hypothesis. An identical transcript for all issuer hypotheses therefore requires a full under every hypothesis. One authorization can absorb several publications; no transaction is required when there is no access.')
p('Minimum number of authorizations',True)
p('The common policy refreshes at the first access where it must. A later last authorization absorbs more publications and expires later under TTL. By induction, the kth full of any feasible alternative occurs no later than the kth full of the common policy. No alternative can use fewer full calls. With fixed coefficients and full more expensive than hit, this also minimizes access-gas cost.')
p('Boundary of the claim',True)
p('Mandatory own-event invalidation is an architectural assumption. Hidden access classes, private witness updates or an independent status check on a hit require a different argument. Minimum authorization count need not minimize monetary expenditure with changing gas prices; the package includes an early-cheap-refresh counterexample.')
p('Randomization and zero probabilities',True)
p('For an isolated update, a full has probability 1 for its own issuer and rho for a foreign issuer. A hit has probability 0 for its own issuer and 1-rho for a foreign issuer. Thus the worst-case two-sided likelihood ratio is infinite whenever rho is below 1. The expression ln(1/rho) describes only the full outcome. An additive-slack guarantee for this isolated event requires slack at least 1-rho; no composition guarantee is claimed.')
p('A finite two-sided likelihood-ratio guarantee over complete transcripts requires matching support. A hit forbidden under one issuer hypothesis must be forbidden under every hypothesis. The authorization-count bound therefore also applies to randomized policies with that guarantee and zero-error safety.')
p('Full definitions and proofs are in proofs/CONDITIONAL_RESULTS.md. Monotonicity and support arguments are standard. The possible contribution is their scoped application, quantitative boundary and economic calibration, not the invention of intersection or selective-failure attacks.')

page('One coin per publication')
p('Each foreign publication is selected once for cover with probability rho. A skipped event is not retried on the next access. Own-issuer publications always require refresh. Any later full, including a TTL refresh, absorbs all preceding events.')
p('The weekly case has four issuers, 90 days, 100 accesses, TTL 30 days, zero grace and 12 rotating publications. Each issuer has three own and nine foreign events. The exact expected number of authorizations is 4+9rho. Final candidate count follows 1+Binomial(3,rho cubed); residual entropy is the expected base-2 logarithm of that count.')
fig('01_one_coin_frontier.png','Figure 1. Exact expectations, checked against 4,096 binary histories at every point. Initial entropy is 2 bits.')
rows=[]
for rho in [0,.25,.75,.95,1]:
    r=next(x for x in weekly if float(x['rho'])==rho)
    rows.append([str(rho),f"{float(r['expected_authorizations']):.2f}",f"{float(r['gas_proxy'])/1e6:.3f}",f"{float(r['entropy_bits']):.3f}",f"{float(r['singleton_probability'])*100:.2f}%"])
table(['rho','Expected fulls','Million gas','Entropy in bits','Singleton'],rows,[1.4,3.6,3.7,4.5,3.8])
p('Common invalidation requires 13 authorizations and 10,615,258 gas per holder; selective invalidation requires 4 and 8,022,007. The difference is 2,593,251 gas. Selective saves 24.43% relative to common; common costs 32.33% more relative to selective. These use different denominators.')
p('At rho=0.75, the issuer is identified exactly in 19.32% of histories; at rho=0.95, in 0.29%. Singleton probability differs from successful guessing: an observer can guess among several candidates. Bayes accuracy is reported separately. These findings concern this horizon and schedule.')

page('What anonymous publication histories reveal')
p('The observer receives anonymous publication times and linkable holder full/hit histories. True issuers and class labels are excluded from its input. Holder handles are shuffled and access schedules are independently sampled. Ground truth is used only for evaluation.')
fig('02_anonymous_clustering.png','Figure 2. Fixed clustering algorithm, 20 seeds per point. ARI=1 means exact class recovery; ARI near zero indicates chance agreement. The full grid covers 16/32/64 holders.')
p('At the selected 32-holder point, each issuer has eight holders and an expected 12 publications over 90 days; each holder makes 100 accesses. All four selective-policy classes are recovered in all 20 runs. One known holder can correctly label seven other members of its cluster, not the entire population.')
rows=[]
for policy,label in [('selective','Selective'),('coin_0.25','rho=0.25'),('coin_0.75','rho=0.75'),('coin_0.95','rho=0.95'),('common','Common')]:
    r=next(x for x in cluster if x['holders_per_issuer']=='8' and x['accesses']=='100' and x['nu']=='12' and x['policy']==policy)
    rows.append([label,f"{float(r['ari_mean']):.4f}",f"{float(r['pair_auc_mean']):.3f}",f"{float(r['anchor_precision_pooled'])*100:.1f}%"])
table(['Policy','ARI','Pair AUC','Correct among attributed'],rows,[4,2.5,3,7.5])
p('Strong cover often makes this simple algorithm produce incorrect clusters. Propagating an issuer label from one known holder then creates false attributions. The CSVs report coverage and correct and incorrect links; precision alone is insufficient.')
p('This is not a demonstrated attack on the Ethereum Foundation design. Applying the result requires evidence of linkable accesses and an observable full/hit channel. A shared registry with anonymous publications does not itself establish either condition.')

page('Availability across the full sensitivity grid')
p('With visible attempts and perfect hiding, one unsafe issuer hypothesis requires a common rejection. Under a support requirement of at least k candidates, both nonempty accept/deny branches must retain at least k candidates. This is a supporting set-partition lemma, not a new general theory of anonymity.')
fig('03_availability_grid.png','Figure 3. Four issuers and k=2. Daily transition probabilities are sensitivity assumptions, not estimated deployment reliability.',width=16)
p('The grid covers 4/8 issuers, daily outage probabilities 0.02/0.1, daily recovery probabilities 0.2/0.5, freshness caps of 1/3/7 days, three support thresholds and 20 seeds. An online issuer publishes a heartbeat at the start of each day. Availability is the fraction of scheduled requests accepted.')
p('At n=4, k=2, freshness cap 1 day, outage probability 0.1 and recovery probability 0.5, common admission gives 49.56% availability, current fresh-k 82.72% and the history guard 69.25%. Fresh-k does not preserve support after intersecting histories. At k=3, the guard reduces to common admission.')
p('A larger freshness cap improves availability while accepting older status. The guard maximizes accepted candidate count at one step; fairness and service quality across the entire history are not proved. Downtime valuation and optimal heartbeat frequency are unmeasured.')
p('ABC4Trust D2.2 discusses selective revocation and update timing. Disclosure and intersection attacks have earlier treatments by Danezis and Serjantov. CRL/OCSP freshness and Rivest recency requirements provide related context. Full sources and distinctions are in review/RELATED_WORK.md.')

page('Economic incidence and the next task')
p('Common invalidation consumes additional gas. A payment rule changes who finances that gas, not the resource total. The supplied coalition costs include later negative event differences caused by TTL shifts. Aggregate costs remain balanced.')
fig('04_compensation.png','Figure 4. The two issuer-funded allocations for modeled asymmetric A=32. Both reimburse 116,120,017 gas equivalent. The beneficiary benchmark below instead charges holders.')
p('Compare SELF with three allocation rules: foreign-publication frequency, Shapley marginal externality and beneficiary pays. The beneficiary benchmark divides the total common-minus-selective premium equally across all active holders, regardless of their issuer. Each group bears its selective baseline plus its holder count times the common per-person premium. Net settlement among holder groups reconciles this allocation with gas they actually paid. Issuers pay no reimbursement under this benchmark.')
p('In symmetric weekly A=4, each issuer pays 2,593,251 gas equivalent under either issuer-funded rule and its own holder receives the same amount. Consolidating each issuer with its affiliated holder gives a zero net transfer; these remain distinct economic actors. The beneficiary rule coincides with SELF here. Use asymmetric A=32 to examine distributional differences.')
p('The weekly premium is 10,373,004 gas for four holders. At historical q0=0.130658648 gwei and EUR/ETH=2,164.73, that is about EUR 2.93 per group or EUR 0.73 per holder over 90 days. This small reference magnitude must be explicit. Startup, issuance, publications and settlement overhead are outside this access-only comparison.')
p('Nataliya should return a 2–3 page note, the completed 96-row payment table and a short missing-input list by the soft target of 30 November. Check the historical and x10/x100 scenarios, budget balance, administrative effort and reporting incentives. An equal beneficiary allocation is a normative benchmark, not evidence of equal willingness to pay or incentive compatibility.')
p('The prior funding addendum v0.2.1 remains complete. No new paymaster calculation or cryptographic review is requested. Oleksandr retains responsibility for technical inputs and independent assessment of the claims and novelty. The short entry point is handoff/START_HERE.md.')

# Remove inherited decorative paragraph rules from the document and styles.
for element in [doc._element, doc.styles.element]:
    for border in list(element.iter(qn('w:pBdr'))):
        border.getparent().remove(border)
doc.save(ROOT/'ECON08_Observability_Review_EN_v0_2.docx')
print('English review created: six planned pages')
