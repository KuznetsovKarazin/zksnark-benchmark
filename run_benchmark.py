#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import List

# Ensure src/ is on sys.path
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from benchmark.runner import (
    BenchmarkRunner,
    BenchmarkConfig,
    load_config_from_yaml,
)

def _load_yaml_configs(config_path: Path) -> List[BenchmarkConfig]:
    return load_config_from_yaml(config_path)


def _print_tool_status(status: dict) -> None:
    print("\nTool Status:\n" + "=" * 40)
    for k, v in status.items():
        avail = v.get("available", False)
        if avail:
            ver = v.get("version", "unknown")
            path = v.get("path", "")
            print(f"✓ {k}: {ver} ({path})")
        else:
            err = v.get("error", "unknown")
            path = v.get("path", "")
            print(f"✗ {k}: {err} ({path})")
    print("")


def _print_summary(results: List[dict]) -> None:
    if not results:
        print("No results."); return
    total = len(results)
    succ = [r for r in results if r.get("success")]
    fail = total - len(succ)
    print("\nBenchmark Summary:")
    print("=" * 50)
    print(f"Total runs: {total}")
    print(f"Successful: {len(succ)}")
    print(f"Failed: {fail}")
    if succ:
        avg_total = sum(r["total_time_s"] for r in succ) / len(succ)
        avg_prove = sum(r["prove_time_s"] for r in succ) / len(succ)
        avg_verify = sum(r["verify_time_s"] for r in succ) / len(succ)
        avg_cons = sum(r["constraints"] for r in succ) / len(succ)
        avg_psz  = sum(r["proof_size_bytes"] for r in succ) / len(succ)
        print(f"\nTiming (successful runs):")
        print(f"  Average total time: {avg_total:.3f}s")
        print(f"  Average prove time: {avg_prove:.3f}s")
        print(f"  Average verify time: {avg_verify:.3f}s")
        print(f"\nCircuit metrics:")
        print(f"  Average constraints: {avg_cons:.1f}")
        print(f"  Average proof size: {int(avg_psz)} bytes")
    print("")


def main() -> None:
    ap = argparse.ArgumentParser(description="ZK-SNARK benchmark runner")
    ap.add_argument("--verify-tools", action="store_true", help="check tool availability and exit")
    ap.add_argument("--circuit", type=str, help="path to .circom file")
    ap.add_argument("--config", type=str, help="YAML config path")
    ap.add_argument("--iterations", type=int, default=None, help="override iterations for --circuit")
    ap.add_argument("--ptau-power", type=int, default=None, help="override ptau power")
    ap.add_argument("--workdir", type=str, default="data/benchmarks", help="work directory")
    ap.add_argument("--append", action="store_true", help="append results to results.jsonl instead of overwriting")

    args = ap.parse_args()

    work_dir = Path(args.workdir)
    runner = BenchmarkRunner(work_dir=work_dir)

    tool_status = runner.verify_tools()
    env_meta = {
        "timestamp": time.time(),
        "host": os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME"),
        "python": sys.version.split()[0],
    }
    try:
        import platform, psutil  # psutil is optional
        env_meta["os"] = platform.platform()
        env_meta["cpu_count"] = os.cpu_count()
        if "NODE_OPTIONS" in os.environ:
            env_meta["NODE_OPTIONS"] = os.environ["NODE_OPTIONS"]
        try:
            env_meta["ram_total_gb"] = round(psutil.virtual_memory().total / (1024**3), 2)
        except Exception:
            pass
    except Exception:
        pass

    meta_path = work_dir / "metadata.json"
    meta_path.write_text(json.dumps({"tools": tool_status, "env": env_meta}, indent=2), encoding="utf-8")


    if args.verify_tools:
        _print_tool_status(runner.verify_tools())
        # Soft hint for snarkjs
        st = runner.verify_tools()
        if not st.get("snarkjs", {}).get("available", False):
            print("Some tools are missing. Please install required dependencies.")
        return

    configs: List[BenchmarkConfig] = []

    if args.circuit and args.config:
        raise SystemExit("Use either --circuit or --config, not both.")

    if args.circuit:
        cpath = Path(args.circuit)
        if not cpath.exists():
            raise SystemExit(f"Circuit not found: {cpath}")
        cfg = BenchmarkConfig(
            circuit_name=cpath.stem,
            circuit_path=cpath,
            iterations=(args.iterations or 1),
            ptau_power=args.ptau_power,
            seed=42,
            output_name=None,
        )
        configs = [cfg]
    elif args.config:
        configs = _load_yaml_configs(Path(args.config))
        # Optional CLI override of ptau/iterations for all configs
        if args.ptau_power is not None:
            configs = [BenchmarkConfig(
                circuit_name=cfg.circuit_name,
                circuit_path=cfg.circuit_path,
                iterations=cfg.iterations,
                ptau_power=max(cfg.ptau_power or 0, args.ptau_power),
                seed=cfg.seed,
                output_name=cfg.output_name,
            ) for cfg in configs]
        if args.iterations is not None:
            configs = [BenchmarkConfig(
                circuit_name=cfg.circuit_name,
                circuit_path=cfg.circuit_path,
                iterations=args.iterations,
                ptau_power=cfg.ptau_power,
                seed=cfg.seed,
                output_name=cfg.output_name,
            ) for cfg in configs]
    else:
        raise SystemExit("Provide either --circuit or --config (or --verify-tools).")

    results = runner.run_multiple_benchmarks(configs)
    # Save JSONL
    out_file = work_dir / "results.jsonl"
    runner.save_results_jsonl(results, out_file, append=args.append)
    print(f"Results saved to: {out_file}")
    # Pretty print summary
    results_dicts = [json.loads(json.dumps(r.__dict__, default=str)) for r in results]
    _print_summary(results_dicts)


if __name__ == "__main__":
    try:
        main()
    except ModuleNotFoundError as e:
        print(f"Import error: {e}")
        print("Please ensure all modules are properly installed.")
        print("Try: pip install -e .")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
