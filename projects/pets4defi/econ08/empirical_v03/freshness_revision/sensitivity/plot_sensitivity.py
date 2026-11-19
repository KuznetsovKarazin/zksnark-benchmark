"""Build the manuscript figure from aggregate tables. Requires matplotlib."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "results"
OUT = HERE.parent.parent / "figures"


def read_csv(name):
    with (DATA / name).open() as f:
        return list(csv.DictReader(f))


def main():
    stats = {r["cohort"]: r for r in read_csv("aave_activity_cohorts.csv")}
    costs = {(r["cohort"], int(r["F_hours"])): r for r in read_csv("aave_cohort_frontier.csv")}
    cohorts = ["all", "empty", "cap_10", "empty_cap_10"]
    labels = ["All", "Empty code", "Cap 10/day", "Empty + cap"]
    colors = ["#24475e", "#d2843f", "#549293", "#7c5486"]
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                         "pdf.fonttype": 42, "axes.titlelocation": "left"})
    fig, axes = plt.subplots(1, 3, figsize=(9.5, 3.8), layout="constrained")
    pos = np.arange(len(cohorts))
    short_axis, proof_axis, response_axis = axes
    short_axis.barh(pos + .18, [100 * float(stats[k]["pooled_short_fraction"]) for k in cohorts],
                    height=.34, color=colors[0], label="Each interval")
    short_axis.barh(pos - .18, [100 * float(stats[k]["wallet_mean_short_fraction"]) for k in cohorts],
                    height=.34, color="#91aaa9", label="Each wallet")
    short_axis.set_yticks(pos, labels)
    short_axis.invert_yaxis()
    short_axis.set(xlim=(0, 100), xlabel="Intervals below one hour (%)", title="A   Access concentration")
    short_axis.legend(loc="lower right", frameon=False, fontsize=8)
    hours = [1, 6, 24]
    for index, (k, name, color) in enumerate(zip(cohorts, labels, colors)):
        line = "-" if index in (0, 3) else "--"
        proof_axis.plot(range(3), [float(costs[k, h]["common_minus_selective"]) for h in hours],
                        color=color, linestyle=line, marker=["o","s","^","D"][index], ms=4, label=name)
    proof_axis.set(title="B   Cost of the shared epoch", ylabel="Extra full proofs per wallet",
                   xlabel="Maximum revocation age (hours)", xticks=range(3), xticklabels=hours)
    proof_axis.set_ylim(bottom=0)
    proof_axis.legend(frameon=False, fontsize=8)
    for field, name, color, style in [
        ("selective_switch_access_weighted", "Selective, each access", colors[0], "-"),
        ("selective_switch_wallet_weighted", "Selective, each wallet", colors[2], "--"),
        ("shared_switch_access_weighted", "Shared or fixed batch", colors[1], ":")]:
        response_axis.plot(range(3), [100 * float(costs["all", h][field]) for h in hours],
                           marker="o", color=color, linestyle=style, ms=4, label=name)
    response_axis.set(title="C   Dependence on issuer schedule", ylabel="Different cache decisions (%)",
                      xlabel="Maximum revocation age (hours)", xticks=range(3), xticklabels=hours)
    response_axis.set_ylim(bottom=-1)
    response_axis.legend(frameon=False, fontsize=8)
    for ax in axes[1:]:
        ax.grid(axis="y", alpha=.20)
    for suffix in ("pdf", "png"):
        options = {"metadata": {"CreationDate": None}} if suffix == "pdf" else {"dpi": 180}
        fig.savefig(OUT / ("aave_access_sensitivity." + suffix), **options)
    plt.close(fig)


if __name__ == "__main__":
    main()
