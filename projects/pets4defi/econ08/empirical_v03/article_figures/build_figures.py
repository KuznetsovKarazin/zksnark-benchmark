"""Rebuild manuscript figures and numerical table rows from released aggregates.

Run from the Overleaf project directory with Python 3, matplotlib and numpy.
The script operates only on the included public aggregate inputs.
"""
from pathlib import Path
from datetime import date
from decimal import Decimal as D
from statistics import median
from collections import defaultdict
import csv
import gzip
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

ROOT = Path(__file__).resolve().parent
DATA, FIGS, TABLES = (ROOT / k for k in ("figure-data", "figures", "tables"))
FIGS.mkdir(exist_ok=True)
TABLES.mkdir(exist_ok=True)
# The article ZIP carries the exact figure inputs. A repository checkout can
# use the same script directly against its immutable source tables.
EMPIRICAL = ROOT.parent
SOURCE_TABLES = {
    "stress_summary.csv": EMPIRICAL / "results/stress/summary.csv",
    "validation_seeds.csv": EMPIRICAL / "seed_validation/seeds.csv",
    "validation_summary.csv": EMPIRICAL / "seed_validation/summary.csv",
    "price_inputs.csv": EMPIRICAL.parent / "observability_v02/handoff/price_inputs.csv",
    "economic_cases.csv": EMPIRICAL.parent / "observability_v02/results/economic_cases.csv",
    "compensation_reference.csv": EMPIRICAL.parent / "observability_v02/results/compensation_reference.csv",
}
def data_path(name):
    if DATA.is_dir():
        return DATA / name
    return SOURCE_TABLES.get(name, EMPIRICAL / "freshness_revision/results" / name)

def read(name):
    with data_path(name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))
def rows(name, body):
    (TABLES / name).write_text("\n".join(" & ".join(row) + r" \\" for row in body) + "\n", encoding="utf-8")
def key(row):
    return row["cohort"], int(row["F_hours"])
costs = {key(r): r for r in read("aave_cohort_frontier.csv")}
paths = {(r["cohort"], int(r["F_hours"]), r["policy"]):r for r in read("aave_path_frontier.csv")}
primary = "empty_cap_10"
deadlines = (1, 6, 24)
schedule = {1:3300, 6:21300, 24:86100}
rates = read("base_fee_quotes.csv")
paired = {}
for r in rates:
    if r["kind"] in ("hit", "full_zk") and r["l2_plus_l1_wei"]:
        paired.setdefault((r["date"],r["block"]), {})[r["kind"]] = int(r["l2_plus_l1_wei"])
daily = {k[0]:D(q["full_zk"]-q["hit"]) for k,q in paired.items() if len(q)==2}
reference = median(daily.values())
def accuracy_k(k, correct=.9):
    return sum(math.comb(k,x) * correct**x * (1-correct)**(k-x) * (1 if 2*x>k else .5 if 2*x==k else 0)
               for x in range(k+1))
for r in paths.values():
    # For symmetric coin flips with random tie-breaking, k=2j and k=2j-1
    # have the same expected accuracy. The published tail gives the sum for k>=9.
    correct = .5 * int(r["count_0"]) + float(r["expected_correct_10pct_in_9_plus"])
    correct += sum(int(r[col]) * accuracy_k(k) for col,k in
                   (("count_1_2",1),("count_3_4",3),("count_5_6",5),("count_7_8",7)))
    assert math.isclose(correct/int(r["wallets"]),float(r["accuracy_10pct"]),rel_tol=1e-12)
activity = {r["cohort"]:r for r in read("aave_activity_cohorts.csv")}
assert int(activity["other_code"]["accesses"])==239031
assert int(activity["all"]["wallets"])-int(activity["cap_10"]["wallets"])==393
reference_fx = next(r for r in read("price_inputs.csv") if r["scenario"]=="historical_reference")
assert D(reference_fx["eth_price_eur"])==D("2164.73")
case_inputs = {(r["case"],r["policy"]):r for r in read("economic_cases.csv")}
assert int(case_inputs["weekly_A4","common"]["premium_gas_vs_selective"])//4==2593251
assert int(case_inputs["asymmetric_A32","common"]["premium_gas_vs_selective"])==116120017
matched = median(v for s,v in daily.items() if "2026-09-08" <= s < "2026-11-05")
assert len(daily)==49 and len([s for s in daily if s<"2026-11-05"])==48
assert reference == D(1411190101406) and matched==D("1411124136948.5")
starts = []
economics = []
for F in deadlines:
    c, p = costs[primary,F], paths[primary,F,"selective"]
    n,q,k = int(c["wallets"]),int(p["distinguishable_wallets"]),int(p["different_decisions"])
    delta=int(c["common_full_sum"])-int(c["intermittent_full_sum"])
    assert n == 9832 and k==delta and c["common_full_sum"]==c["daily_full_sum"]
    assert math.isclose(float(p["accuracy_noiseless"]), 0.5*(1+q/n))
    for policy in ("common","fixed_batch"):
        z=paths[primary,F,policy]
        assert int(z["distinguishable_wallets"])==0 and float(z["accuracy_10pct"])==0.5
    starts.append([str(F),f"{float(c['selective_equal_full']):.3f}",f"{float(c['common_full']):.3f}",
                   f"{float(c['fixed_batch_full']):.3f}",f"{q:,}",f"{100*q/n:.2f}",
                   f"{100*float(p['accuracy_noiseless']):.2f}",f"{100*float(p['accuracy_10pct']):.2f}"])
    premium=reference*delta/D(10**18)
    economics.append([str(F),f"{delta:,}",f"{delta/n:.3f}",f"{delta/(2*n):.3f}",
                      f"{premium:.8f}",f"{premium*10**6/n:.3f}",f"{premium*10**6/(2*n):.3f}"])
rows("frontier.tex", starts)
rows("incidence.tex", economics)

plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":8.5, "axes.spines.top":False,
    "axes.spines.right":False, "axes.labelcolor":"#222222","axes.titlecolor":"#172b3a",
    "axes.edgecolor":"#76838a","axes.linewidth":0.65,"pdf.fonttype":42, "ps.fonttype":42,
    "savefig.transparent":False,"figure.facecolor":"white"})
teal,orange,navy,grey="#006f74","#a64d17","#233f58","#6c7680"
def finish(fig,name):
    fig.savefig(FIGS/name,facecolor="white",metadata={"Creator":"build_figures.py","CreationDate":None,"ModDate":None})
    plt.close(fig)

fig,axes=plt.subplots(1,3,figsize=(7.0,2.85),sharex=True,sharey=True)
for j,(ax,F) in enumerate(zip(axes,deadlines)):
    p,com,bat=(paths[primary,F,pol] for pol in ("selective","common","fixed_batch"))
    xs,xc,xb=(float(row["full_proofs_per_wallet"]) for row in (p,com,bat))
    y0,y1=100*float(p["accuracy_noiseless"]),100*float(p["accuracy_10pct"])
    ax.axhline(50,color=grey,ls=":",lw=.95)
    ax.plot([xs,xc],[y0,50],color=teal,lw=1.25)
    ax.plot([xs,xc],[y1,50],color=orange,lw=1.2,ls="--")
    ax.scatter(xs,y0,marker="o",s=30,color=teal,zorder=4)
    ax.scatter(xs,y1,marker="s",s=27,color=orange,zorder=4)
    ax.scatter(xb,50,marker="o",s=63,color="white",edgecolor=navy,lw=1.1,zorder=3)
    ax.scatter(xc,50,marker="+",s=37,color=navy,lw=1.2,zorder=4)
    # Put the error-label text on the opposite side of both descending lines.
    ax.annotate(f"{y0:.1f}%", (xs, y0), xytext=(5, 4),
                textcoords="offset points", ha="left", va="bottom", fontsize=8.2, color=teal)
    ax.annotate(f"{y1:.1f}%", (xs, y1), xytext=(-5, -6),
                textcoords="offset points", ha="right", va="top", fontsize=8.2, color=orange)
    ax.set_title(f"F = {F} h",fontweight="bold",fontsize=10)
    ax.set_xlim(2.75,4.95);ax.set_ylim(47.5,83);ax.set_xticks([3.5,4,4.5]);ax.set_yticks([50,60,70,80]);ax.grid(axis="y",color="#e0e6e8",lw=.5)
axes[0].set_ylabel("Correct schedule choice (%)")
fig.supxlabel("Full proofs per path over 58 days (equal source weights)",y=.205,fontsize=9)
handles=[Line2D([],[],color=teal,marker="o",lw=1,label="Selective, exact labels"),
         Line2D([],[],color=orange,marker="s",ls="--",lw=1,label="Selective, 10% label error"),
         Line2D([],[],color=navy,marker="o",markerfacecolor="white",lw=0,label="Shared / fixed cadence")]
fig.legend(handles=handles,loc="lower center",ncol=3,frameon=False,fontsize=7.8,handlelength=1.5,columnspacing=1.3,bbox_to_anchor=(.53,.015))
fig.subplots_adjust(left=.095,right=.98,top=.87,bottom=.39,wspace=.16)
finish(fig,"01_frontier.pdf")

names=[("All eligible","all"),("Empty code","empty"),("Delegated","delegated"),("Other code","other_code"),
       ("Empty code, cap 10","empty_cap_10"),("3 accesses","quartile_1"),("4 accesses","quartile_2"),
       ("5–8 accesses","quartile_3"),("9 or more","quartile_4")]
ys=np.array([9,8,7,6,5,3.6,2.6,1.6,.6])
fig,axs=plt.subplots(1,2,figsize=(7.05,3.45),sharey=True,gridspec_kw={"width_ratios":[1,1]})
for ax in axs:
    ax.axhspan(4.6,5.4,color="#e6f0ef",zorder=0);ax.axhline(4.2,color="#c8cccd",lw=.65)
    ax.grid(axis="x",color="#e2e7e8",lw=.65);ax.set_axisbelow(True);ax.set_ylim(.05,9.55)
for (label,c),y in zip(names,ys):
    p=paths[c,1,"selective"];cost=float(costs[c,1]["quiet_extra_under_common"])
    for ax,v,m,clr,dx,txt in [(axs[0],cost,"s",teal,.8,f"{cost:.2f}"),
                              (axs[1],100*float(p["distinguishable_fraction"]),"o",navy,2.1,f"{100*float(p['distinguishable_fraction']):.1f}")]:
        ax.plot([0,v],[y,y],color="#c3ced2",lw=.75);ax.scatter(v,y,s=21,marker=m,color=clr,zorder=3);ax.text(v+dx,y,txt,va="center",fontsize=7.6)
axs[0].set_yticks(ys,[k for k,_ in names]);axs[0].set_xlim(0,34);axs[0].set_xticks([0,10,20,30])
axs[1].set_xlim(0,112);axs[1].set_xticks([0,25,50,75,100])
axs[0].set_title("Extra proofs for the intermittent source",fontsize=9,fontweight="bold")
axs[1].set_title("Paths distinguishable under selective",fontsize=9,fontweight="bold")
axs[0].set_xlabel("Proofs per path, 58 days");axs[1].set_xlabel("Share of paths (%)")
fig.subplots_adjust(left=.205,right=.98,top=.89,bottom=.155,wspace=.14)
finish(fig,"02_cohorts.pdf")

sub=read("subdaily_summary.csv")
fig,axs=plt.subplots(1,3,figsize=(7.0,2.95),sharey=True)
for ax,F in zip(axs,deadlines):
    chosen={(r["policy"],int(r["group_size"])):r for r in sub if r["issuers"]=="16" and r["access_model"]=="session" and int(r["period_s"])==schedule[F]}
    pols=[("group_like_rate",teal,"o","-"),("group_random",orange,"s","--")]
    for pol,col,mark,style in pols:
        series=[chosen["selective",1]]+[chosen[pol,g] for g in (2,4,8)]+[chosen["common",16]]
        ax.plot([float(d["full"]) for d in series],[100*float(d["switch_disagreement"]) for d in series],lw=1.2,ls=style,color=col)
        for d in series[1:-1]:
            x,y=float(d["full"]),100*float(d["switch_disagreement"])
            ax.scatter(x,y,marker=mark,color=col,s=20,zorder=3)
    for pol,g,marker in [("selective",1,"^"),("common",16,"D")]:
        d=chosen[pol,g];ax.scatter(float(d["full"]),100*float(d["switch_disagreement"]),color=navy,marker=marker,s=25,zorder=5)
    ax.set_title(f"F = {F} h",fontsize=10,fontweight="bold");ax.grid(axis="y",color="#e0e6e8",lw=.5);ax.margins(x=.13);ax.set_ylim(-1.7,28.5)
axs[0].set_ylabel("Changed decisions (%)")
fig.supxlabel("Full proofs per holder, 90-day model",fontsize=9,y=.20)
legend=[Line2D([],[],ls="-",marker="o",color=teal,label="Similar-rate groups"),
        Line2D([],[],ls="--",marker="s",color=orange,label="Random groups"),
        Line2D([],[],ls="",marker="^",color=navy,label="Selective"),
        Line2D([],[],ls="",marker="D",color=navy,label="Shared")]
fig.legend(handles=legend,loc="lower center",bbox_to_anchor=(.51,.005),ncol=4,frameon=False,fontsize=7.8,handlelength=1.4,columnspacing=1.4)
fig.subplots_adjust(left=.09,right=.98,top=.88,bottom=.37,wspace=.2)
finish(fig,"03_groups.pdf")

stress=read("stress_summary.csv")
with gzip.open(data_path("eas_slot_counts.csv.gz"),"rt") as stream: easslots=list(csv.DictReader(stream))
start=(date(2026,9,8)-date(2026,8,19)).days*86400
end=start+58*86400
counts=[]
for F in deadlines:
    period=schedule[F]
    covered=[r for r in easslots if int(r["period_s"])==period and start<=int(r["cutoff_offset_s"])+300<end]
    hi=sum(int(r["daily_source_count"])>0 for r in covered)
    lo=sum(int(r["intermittent_source_count"])>0 for r in covered)
    union=sum(bool(int(r["daily_source_count"]) or int(r["intermittent_source_count"])) for r in covered)
    fixed=sum(start<=t+300<end for t in range(period,end+1,period))
    checked = next(r for r in read("trace_freshness.csv") if int(r["period_s"])==period)
    assert hi==union and int(checked["common_registry_writes"])==union and int(checked["batch_registry_writes"])==fixed
    counts.append([str(F),str(period//60),f"{hi:,}",f"{lo:,}",f"{hi+lo:,}",f"{union:,}",f"{fixed:,}"])
rows("slots.tex",counts)
fig,axs=plt.subplots(1,3,figsize=(7.0,2.55),sharey=True)
sizes=(4,8,16,32,64); errors=(0,.05,.10,.20)
values={(int(r["issuers"]),float(r["label_error"]),float(r["missing"])):100*float(r["accuracy"])
        for r in stress if r["policy"]=="selective"}
from matplotlib.colors import LinearSegmentedColormap
cmap=LinearSegmentedColormap.from_list("accuracy",["#edf3f3","#a1ccc5","#3d8984","#184756"])
for j,(ax,missing) in enumerate(zip(axs,(0,.1,.3))):
    arr=np.array([[values[b,err,missing] for b in sizes] for err in errors])
    ax.imshow(arr,vmin=50,vmax=100,cmap=cmap,aspect="auto")
    for y in range(len(errors)):
        for x in range(len(sizes)):
            val=arr[y,x];ax.text(x,y,f"{val:.0f}",ha="center",va="center",fontsize=8,color=("white" if val>=80 else "#182a34"))
    ax.set_xticks(range(5),[str(v) for v in sizes]);ax.set_yticks(range(4),["0","5","10","20"])
    ax.set_title(f"Missing accesses: {missing:.0%}",fontsize=9,fontweight="bold")
    ax.tick_params(length=0);[sp.set_visible(False) for sp in ax.spines.values()]
axs[0].set_ylabel("Label errors (%)")
fig.supxlabel("Number of simulated issuers",fontsize=9,y=.07)
fig.subplots_adjust(left=.085,right=.99,bottom=.26,top=.84,wspace=.13)
finish(fig,"04_synthetic_noise.pdf")
paid, received, public = defaultdict(D), defaultdict(D), {}
for r in read("compensation_reference.csv"):
    if r["case"]!="asymmetric_A32":
        continue
    payer, group, rule = r["paying_issuer"], r["holder_group_issuer"], r["rule"]
    amount=D(r["reimbursement_gas_equivalent"])
    paid[payer,rule]+=amount
    received[group,rule]+=amount
    public[payer]=r["publication_count"]
rules=("publication_frequency","shapley_externality")
historical=[]
for issuer in sorted(public):
    charge=[paid[issuer,r] for r in rules]
    refund=[received[issuer,r] for r in rules]
    assert abs(refund[0]-refund[1])<D("0.00001")
    historical.append([issuer,public[issuer]]+[f"{v/D(10**6):.3f}" for v in (*charge,refund[0])])
assert all(abs(sum(paid[i,r] for i in public)-D(116120017))<D("0.00001") for r in rules)
rows("historical_incidence.tex",historical)

# Check and format the positive synthetic validation using independent seed units.
validation = read("validation_seeds.csv")
reference_stats = {(int(r["issuers"]), r["metric"]): r for r in read("validation_summary.csv")}
table = []
for issuers in (4, 64):
    sample = [r for r in validation if int(r["issuers"]) == issuers]
    assert sorted(int(r["seed"]) for r in sample) == list(range(30001, 30011))
    cells = [str(issuers)]
    for metric, scale, decimals in (
        ("known_accuracy", 100, 2), ("estimated_accuracy", 100, 2),
        ("paired_difference", 100, 2), ("ari", 1, 3), ("nonanchor_accuracy", 100, 2)
    ):
        values = np.array([float(r[metric]) for r in sample])
        center = values.mean()
        half = 2.2621571628540993 * values.std(ddof=1) / np.sqrt(len(sample))
        recorded = reference_stats[issuers, metric]
        assert np.isclose(center, float(recorded["mean"]), atol=1e-12)
        assert np.isclose(half, float(recorded["ci95_halfwidth"]), atol=1e-12)
        cells.append(f"{scale*center:.{decimals}f}" + r"\,$\pm$\," + f"{scale*half:.{decimals}f}")
    table.append(cells)
rows("seed_validation.tex", table)

print("Rebuilt four figures and five numerical tables. Fee and independent-seed checks passed.")
