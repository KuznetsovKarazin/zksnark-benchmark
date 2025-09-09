# easy_batch.py
# Minimal runner for multiple circuits with per-circuit iteration counts and averaging.
# It only depends on run_benchmark.py and data/benchmarks/results.jsonl.

import os, sys, json, time, subprocess, csv
from pathlib import Path
from collections import defaultdict

# --- Configuration ------------------------------------------------------------

RESULTS_JSONL = Path("data/benchmarks/results.jsonl")
LOG_DIR       = Path("data/benchmarks/batch_logs")
OUT_DIR       = Path("data/benchmarks/batch_runs")

# Iterations by circuit (tune as you like)
CIRCUITS = [
    # (path_to_circom, iterations)
    ("src/circuits/basic/range_proof.circom",       10),  # simple
    ("src/circuits/crypto/hash.circom",             10),  # simple
    ("src/circuits/crypto/merkle_poseidon_4.circom", 3),  # complex
]

RUN_BENCH = "run_benchmark.py"
EXTRA_ARGS = ["--append"]  # keep appending to results.jsonl

# Optional pause between runs (seconds)
SLEEP_BETWEEN = 0.0

# --- Helpers -----------------------------------------------------------------

def ensure_dirs():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

def count_lines(p: Path) -> int:
    if not p.exists():
        return 0
    with p.open("rb") as f:
        return sum(1 for _ in f)

def read_new_jsonl(p: Path, skip: int):
    """Read only lines with index >= skip; parse JSON if possible."""
    out = []
    if not p.exists():
        return out
    with p.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i < skip:
                continue
            s = line.strip()
            if not s:
                continue
            try:
                out.append(json.loads(s))
            except Exception:
                # ignore non-JSON lines
                pass
    return out

def run_once(circuit: str, iter_idx: int) -> int:
    """Run run_benchmark.py for a single iteration; never raises."""
    cmd = [sys.executable, RUN_BENCH, "--circuit", circuit, "--iterations", "1", *EXTRA_ARGS]
    log_path = LOG_DIR / f"{Path(circuit).stem}_iter{iter_idx:02d}.log"
    with log_path.open("w", encoding="utf-8") as logf:
        logf.write("> " + " ".join(cmd) + "\n")
        try:
            res = subprocess.run(cmd, text=True, capture_output=True)
            logf.write(res.stdout or "")
            if res.stderr:
                logf.write("\n--- STDERR ---\n")
                logf.write(res.stderr)
            return res.returncode
        except Exception as e:
            logf.write(f"\n[runner] exception: {e}\n")
            return 99

def pick(d: dict, *names, default=None):
    """Pick first matching key by name (case-insensitive)."""
    lower = {k.lower(): k for k in d.keys()}
    for n in names:
        k = lower.get(n.lower())
        if k is not None:
            return d[k]
    return default

def to_float(x):
    try:
        return float(x)
    except Exception:
        return float("nan")

def mean(xs):
    xs = [to_float(x) for x in xs if x is not None]
    xs = [x for x in xs if x == x]  # drop NaN
    return sum(xs)/len(xs) if xs else float("nan")

def std(xs):
    xs = [to_float(x) for x in xs if x is not None]
    xs = [x for x in xs if x == x]
    if len(xs) < 2:
        return float("nan")
    m = sum(xs)/len(xs)
    return (sum((x-m)**2 for x in xs)/(len(xs)-1))**0.5

# --- Main --------------------------------------------------------------------

def main():
    ensure_dirs()
    baseline = count_lines(RESULTS_JSONL)
    print(f"[easy] baseline lines in {RESULTS_JSONL}: {baseline}")

    # Run circuits sequentially; each iteration is a separate run (robust to failures)
    for circuit, iters in CIRCUITS:
        print(f"\n[easy] {circuit} x{iters}")
        for i in range(1, iters + 1):
            rc = run_once(circuit, i)
            status = "OK" if rc == 0 else f"RC={rc}"
            print(f"  iter {i}/{iters}: {status}")
            if SLEEP_BETWEEN > 0:
                time.sleep(SLEEP_BETWEEN)

    # Read only new JSON records appended during this session
    records = read_new_jsonl(RESULTS_JSONL, baseline)
    if not records:
        print(f"\n[easy][WARN] No new JSON records found in {RESULTS_JSONL}. "
              f"Check logs in {LOG_DIR} for errors.")
        return 2

    # Aggregate by circuit
    by_circ = defaultdict(list)
    for r in records:
        circ = pick(r, "circuit", "name", "circuit_path", default="unknown")
        by_circ[circ].append(r)

    # Build compact summary
    summary_rows = []
    for circ, rows in by_circ.items():
        # success / fail
        statuses = [str(pick(r, "status", "result", "ok", default="")).lower() for r in rows]
        ok = sum(1 for s in statuses if s in ("success","ok","true","passed","pass"))
        fail = len(rows) - ok

        # times (try several aliases)
        get_t = lambda r, *ks: pick(r, *ks, default=None)
        comp = [get_t(r, "compile_s","compile","compile_time","compile_time_s") for r in rows]
        wit  = [get_t(r, "witness_s","witness","generate_witness_s") for r in rows]
        prv  = [get_t(r, "prove_s","prove","prove_time","prove_time_s") for r in rows]
        ver  = [get_t(r, "verify_s","verify","verify_time","verify_time_s") for r in rows]
        tot  = [get_t(r, "total_s","total_time","total_time_s","duration_s") for r in rows]

        stage_means = {
            "compile_s_avg": mean(comp),
            "witness_s_avg": mean(wit),
            "prove_s_avg":   mean(prv),
            "verify_s_avg":  mean(ver),
        }
        dom_stage = max(stage_means, key=lambda k: (stage_means[k] if stage_means[k] == stage_means[k] else -1))

        summary_rows.append({
            "circuit": circ,
            "runs": len(rows),
            "success": ok,
            "fail": fail,
            "compile_s_avg": stage_means["compile_s_avg"],
            "compile_s_std": std(comp),
            "witness_s_avg": stage_means["witness_s_avg"],
            "witness_s_std": std(wit),
            "prove_s_avg":   stage_means["prove_s_avg"],
            "prove_s_std":   std(prv),
            "verify_s_avg":  stage_means["verify_s_avg"],
            "verify_s_std":  std(ver),
            "total_s_avg":   mean(tot),
            "total_s_std":   std(tot),
            "dominant_stage": dom_stage
        })

    # Sort by fail desc, then by name
    summary_rows.sort(key=lambda r: (-r["fail"], str(r["circuit"]).lower()))

    # Write summary CSV
    tag = time.strftime("%Y%m%d_%H%M%S")
    out_csv = OUT_DIR / f"easy_summary_{tag}.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        w.writeheader()
        for row in summary_rows:
            w.writerow(row)

    print("\n[easy] Summary:")
    for row in summary_rows:
        print(f"  - {row['circuit']}: runs={row['runs']} ok={row['success']} "
              f"total_s_avg={row['total_s_avg']:.4f}")

    print(f"\n[easy] Saved summary to: {out_csv}")
    print(f"[easy] Logs: {LOG_DIR}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
