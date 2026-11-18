"""Plot paired cost and expected accuracy for the prespecified primary cohort."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import PercentFormatter

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "results" / "aave_path_frontier.csv"
OUTPUT = HERE.parent.parent / "figures"


def main():
    with SOURCE.open() as stream:
        rows = [r for r in csv.DictReader(stream) if r["cohort"] == "empty_cap_10"]
    colors = {1: "#195477", 6: "#bb4f27", 24: "#16816e"}
    marks = {"selective": ("o", "Selective"), "common": ("s", "Shared epoch"),
             "fixed_batch": ("+", "Fixed batch")}
    plt.rcParams.update({"font.size": 10, "pdf.fonttype": 42,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(7.5, 3.65), sharex=True, sharey=True)
    fig.subplots_adjust(left=.095, right=.98, top=.85, bottom=.31, wspace=.12)
    for ax, field, title in zip(axes, ("accuracy_noiseless", "accuracy_10pct"),
                                ("Perfect labels", "10% independent label errors")):
        ax.set_title(title, loc="left", fontsize=11)
        ax.axhline(.5, color="#858585", linewidth=.8, linestyle=":", zorder=0)
        ax.grid(axis="y", color="#e0e0e0", linewidth=.6)
        for row in rows:
            policy = row["policy"]
            color = colors[int(row["F_hours"])]
            ax.plot(float(row["full_proofs_per_wallet"]), float(row[field]),
                    marker=marks[policy][0], color=color, linestyle="none",
                    markerfacecolor=color if policy == "selective" else "none",
                    markersize=8 if policy == "common" else 6, markeredgewidth=1.5)
        ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
        ax.set_ylim(.465, 1.01)
        ax.set_xlabel("Full proofs per wallet in 58 days")
        ax.margins(x=.16)
    axes[0].set_ylabel("Expected correct assignment")
    handles = [Line2D([], [], color=c, linewidth=3, label=f"F = {h} h") for h, c in colors.items()]
    handles.extend(Line2D([], [], color="#303942", marker=m, markerfacecolor="#303942" if k=="selective" else "none",
                          linestyle="none", label=label) for k,(m,label) in marks.items())
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(.5,.016), ncol=3,
               frameon=False, columnspacing=2.4)
    for suffix in ("pdf", "png"):
        options = {"metadata": {"CreationDate": None}} if suffix == "pdf" else {"dpi": 200}
        fig.savefig(OUTPUT / ("aave_path_frontier." + suffix), **options)
    plt.close(fig)


if __name__ == "__main__":
    main()
