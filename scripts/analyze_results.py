#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, os, time
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

import numpy as np

# no seaborn; one chart per figure; no custom colors

REQUIRED_COLS = [
    "config.circuit_name","config.ptau_power","success","constraints",
    "compile_time_s","setup_time_s","witness_time_s","prove_time_s","verify_time_s",
    "total_time_s","proof_size_bytes","public_size_bytes","peak_rss_mb","timestamp"
]


def fit_scaling_alpha(df: pd.DataFrame, metric: str) -> dict:
    ok = df[(df["success"]) & (df[metric] > 0) & (df["constraints"] > 0)].copy()
    if ok.shape[0] < 2:
        return {"alpha": None, "k": None, "n": ok.shape[0]}
    x = np.log(ok["constraints"].values.astype(float))
    y = np.log(ok[metric].values.astype(float))
    A = np.vstack([x, np.ones_like(x)]).T
    alpha, b = np.linalg.lstsq(A, y, rcond=None)[0]  # y = alpha*x + b
    k = float(np.exp(b))
    return {"alpha": float(alpha), "k": k, "n": int(ok.shape[0])}

def plot_with_regression(df: pd.DataFrame, metric: str, out_png: Path) -> None:
    ok = df[(df["success"]) & (df[metric] > 0) & (df["constraints"] > 0)].copy()
    if ok.empty: return
    plt.figure()
    # точки
    for name, g in ok.groupby("circuit"):
        plt.loglog(g["constraints"], g[metric], marker="o", linestyle="", label=name)
    # регрессия по всем точкам
    x = np.log(ok["constraints"].values.astype(float))
    y = np.log(ok[metric].values.astype(float))
    A = np.vstack([x, np.ones_like(x)]).T
    alpha, b = np.linalg.lstsq(A, y, rcond=None)[0]
    xs = np.linspace(x.min(), x.max(), 100)
    ys = alpha*xs + b
    plt.loglog(np.exp(xs), np.exp(ys))
    plt.xlabel("Constraints (log)"); plt.ylabel(f"{metric} (s, log)")
    plt.title(f"{metric} vs constraints (fit α={alpha:.3f})")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png, dpi=160)
    plt.close()


def load_jsonl(path: Path) -> pd.DataFrame:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line: continue
            rows.append(json.loads(line))
    df = pd.json_normalize(rows)
    # rename for convenience
    if "config.circuit_name" in df.columns:
        df = df.copy()
        df.rename(columns={
            "config.circuit_name":"circuit",
            "config.ptau_power":"ptau_power",
            "config.iterations":"iterations",
            "config.seed":"seed",
        }, inplace=True)
    elif "config" in df.columns:
        # fallback if not flattened
        df["circuit"] = df["config"].apply(lambda x: x.get("circuit_name"))
        df["ptau_power"] = df["config"].apply(lambda x: x.get("ptau_power"))
    else:
        raise SystemExit("results.jsonl has unexpected structure")
    # types & defaults
    for c in ["constraints","proof_size_bytes","public_size_bytes","peak_rss_mb",
              "compile_time_s","setup_time_s","witness_time_s","prove_time_s","verify_time_s","total_time_s"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "ptau_power" in df.columns:
        df["ptau_power"] = pd.to_numeric(df["ptau_power"], errors="coerce")
    if "success" in df.columns:
        df["success"] = df["success"].astype(bool)
    if "timestamp" in df.columns:
        df["ts"] = pd.to_datetime(df["timestamp"], unit="s")
    # keep only relevant cols if present
    keep = [c for c in [
        "circuit","ptau_power","success","constraints",
        "compile_time_s","setup_time_s","witness_time_s","prove_time_s","verify_time_s",
        "total_time_s","proof_size_bytes","public_size_bytes","peak_rss_mb","ts"
    ] if c in df.columns]
    return df[keep]

def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def save_summary_tables(df: pd.DataFrame, outdir: Path) -> dict[str, Path]:
    paths = {}
    # overall summary
    overall = {
        "total_runs": len(df),
        "successful": int(df["success"].sum()),
        "failed": int((~df["success"]).sum()),
        "success_rate_%": round(100*df["success"].mean(), 2),
    }
    overall_df = pd.DataFrame([overall])
    overall_path = outdir/"summary_overall.csv"
    overall_df.to_csv(overall_path, index=False); paths["overall"]=overall_path

    # per-circuit aggregates (successful only)
    ok = df[df["success"]].copy()
    agg = ok.groupby("circuit").agg(
        runs=("circuit","count"),
        constraints=("constraints","median"),
        ptau_power=("ptau_power","max"),
        total_mean_s=("total_time_s","mean"),
        prove_mean_s=("prove_time_s","mean"),
        verify_mean_s=("verify_time_s","mean"),
        setup_mean_s=("setup_time_s","mean"),
        witness_mean_s=("witness_time_s","mean"),
        proof_size_mean=("proof_size_bytes","mean"),
        rss_peak_mb_mean=("peak_rss_mb","mean"),
    ).reset_index().sort_values(["constraints","circuit"])
    agg_path = outdir/"summary_by_circuit.csv"
    agg.to_csv(agg_path, index=False); paths["by_circuit"]=agg_path

    # raw export
    raw_path = outdir/"raw_results.csv"
    df.to_csv(raw_path, index=False); paths["raw"]=raw_path

    return paths

def plot_time_vs_constraints(df: pd.DataFrame, metric: str, out_png: Path) -> None:
    ok = df[df["success"]].copy()
    if ok.empty: return
    plt.figure()
    for name, g in ok.groupby("circuit"):
        x = g["constraints"]
        y = g[metric]
        plt.loglog(x, y, marker="o", linestyle="", label=name)
    plt.xlabel("Constraints (log)")
    plt.ylabel(f"{metric} (s, log)")
    plt.title(f"{metric} vs constraints")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png, dpi=160)
    plt.close()

def plot_stacked_time_breakdown(df: pd.DataFrame, out_png: Path) -> None:
    ok = df[df["success"]].copy()
    if ok.empty: return
    # take median per circuit
    med = ok.groupby("circuit").median(numeric_only=True)[
        ["setup_time_s","witness_time_s","prove_time_s","verify_time_s"]
    ].sort_values("prove_time_s", ascending=False)
    plt.figure()
    idx = range(len(med))
    bottom = [0]*len(med)
    for col in ["setup_time_s","witness_time_s","prove_time_s","verify_time_s"]:
        vals = med[col].values
        plt.bar(idx, vals, bottom=bottom, label=col)
        bottom = [b+v for b,v in zip(bottom, vals)]
    plt.xticks(list(idx), med.index, rotation=30, ha="right")
    plt.ylabel("seconds")
    plt.title("Median time breakdown per circuit")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png, dpi=160)
    plt.close()

def plot_proofsize_vs_constraints(df: pd.DataFrame, out_png: Path) -> None:
    ok = df[df["success"]].copy()
    if ok.empty: return
    plt.figure()
    for name, g in ok.groupby("circuit"):
        plt.scatter(g["constraints"], g["proof_size_bytes"], label=name)
    plt.xscale("log")
    plt.xlabel("Constraints (log)")
    plt.ylabel("Proof size (bytes)")
    plt.title("Proof size vs constraints")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png, dpi=160)
    plt.close()

def render_markdown_report(df: pd.DataFrame, tables: dict[str, Path], figs: dict[str, Path], out_md: Path) -> None:
    lines = []
    lines.append("# ZK Benchmark Report\n")
    lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    if not df.empty:
        circuits = ", ".join(sorted(df["circuit"].unique()))
        lines.append(f"Circuits: {circuits}\n")
        lines.append(f"Total runs: {len(df)}, Success rate: {round(100*df['success'].mean(),2)}%\n")

    lines.append("## Summary tables\n")
    for title, p in [("Overall", tables.get("overall")),
                     ("By circuit", tables.get("by_circuit")),
                     ("Raw results", tables.get("raw"))]:
        if p:
            lines.append(f"- {title}: `{p.as_posix()}`")

    lines.append("\n## Charts\n")
    for title, p in figs.items():
        lines.append(f"### {title}\n")
        lines.append(f"![{title}]({p.as_posix()})\n")

    out_md.write_text("\n".join(lines), encoding="utf-8")

def main():
    ap = argparse.ArgumentParser(description="Analyze benchmark results.jsonl")
    ap.add_argument("--input", type=str, default="data/benchmarks/results.jsonl")
    ap.add_argument("--out", type=str, default=None, help="output dir (default docs/reports/<timestamp>)")
    args = ap.parse_args()

    src = Path(args.input)
    if not src.exists():
        raise SystemExit(f"Input not found: {src}")

    ts_dir = time.strftime("%Y%m%d-%H%M%S")
    outdir = Path(args.out) if args.out else Path("docs/reports")/ts_dir
    ensure_dir(outdir)

    df = load_jsonl(src)

    # tables
    tables = save_summary_tables(df, outdir)

    # figures
    figs = {}
    fig1 = outdir/"time_vs_constraints_total.png"
    plot_time_vs_constraints(df, "total_time_s", fig1);    figs["Total time vs constraints"] = fig1
    fig2 = outdir/"time_vs_constraints_prove.png"
    plot_time_vs_constraints(df, "prove_time_s", fig2);    figs["Prove time vs constraints"] = fig2
    fig3 = outdir/"time_breakdown_stacked.png"
    plot_stacked_time_breakdown(df, fig3);                 figs["Median time breakdown per circuit"] = fig3
    fig4 = outdir/"proofsize_vs_constraints.png"
    plot_proofsize_vs_constraints(df, fig4);               figs["Proof size vs constraints"] = fig4

    # scaling fit
    fit_prove = fit_scaling_alpha(df, "prove_time_s")
    fit_total = fit_scaling_alpha(df, "total_time_s")

    (Path(outdir) / "scaling_alpha.txt").write_text(
        f"prove_time_s: alpha={fit_prove['alpha']}, k={fit_prove['k']}, n={fit_prove['n']}\n"
        f"total_time_s: alpha={fit_total['alpha']}, k={fit_total['k']}, n={fit_total['n']}\n",
        encoding="utf-8"
    )
    pd.DataFrame([
        {"metric":"prove_time_s", **fit_prove},
        {"metric":"total_time_s", **fit_total},
    ]).to_csv(outdir/"scaling_fit.csv", index=False)

    fig5 = outdir/"time_vs_constraints_prove_with_fit.png"
    plot_with_regression(df, "prove_time_s", fig5); figs["Prove time (fit)"] = fig5
    fig6 = outdir/"time_vs_constraints_total_with_fit.png"
    plot_with_regression(df, "total_time_s", fig6); figs["Total time (fit)"] = fig6


    # report
    report_md = outdir/"report.md"
    render_markdown_report(df, tables, figs, report_md)

    print(f"Saved tables and charts to: {outdir}")
    print(f"Report: {report_md}")

if __name__ == "__main__":
    main()
