#!/usr/bin/env python3
"""Run unfiltered Slither scans and retain findings, tool versions and source hashes.

Exit 0: no High/Medium findings; 1: findings need review; 2: tool/setup error.
The intentionally adversarial fixture and generated verifier are scanned too.
No detector, file, or severity is silently suppressed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGETS = {
    "application": ["contracts/AccessGate.sol", "contracts/AccessRegistry.sol", "contracts/MockToken.sol"],
    "generated": ["build/Verifier.sol"],
    "adversarial_fixture": ["contracts/AdversarialToken.sol"],
}


def run_version(command: str) -> str:
    proc = subprocess.run([command, "--version"], capture_output=True, text=True, check=True)
    return (proc.stdout + proc.stderr).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slither", default="slither", help="Slither executable")
    parser.add_argument("--solc", default="solc", help="Native solc 0.8.37 executable")
    parser.add_argument("--out", type=Path, default=Path("results/static_analysis"))
    parser.add_argument("--verifier", type=Path, default=Path("build/Verifier.sol"),
                        help="Generated verifier to scan; can point to a retained CI artifact")
    args = parser.parse_args()
    scan_targets = dict(TARGETS, generated=[str(args.verifier)])
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "slither_version": run_version(args.slither),
        "solc_version": run_version(args.solc),
        "exit_policy": "High or Medium findings in ANY scanned target return exit 1; no automatic waivers",
        "runs": [],
    }
    if "0.8.37+" not in summary["solc_version"]:
        raise RuntimeError("Use native solc 0.8.37 to match the locked benchmark compiler")
    source_hashes = {
        target: hashlib.sha256((ROOT / target).read_bytes()).hexdigest()
        for targets in scan_targets.values() for target in targets
    }
    summary["source_sha256"] = source_hashes
    summary["package_lock_sha256"] = hashlib.sha256((ROOT / "package-lock.json").read_bytes()).hexdigest()
    severe_count = 0
    for group, targets in scan_targets.items():
        for target in targets:
            source = ROOT / target
            if not source.is_file():
                raise FileNotFoundError(f"Missing {target}; run npm run setup first")
            prefix = out / source.stem
            report_path = prefix.with_suffix(".json")
            # Slither refuses to overwrite its own report; remove only that output.
            report_path.unlink(missing_ok=True)
            command = [args.slither, target, "--solc", args.solc, "--json", str(report_path)]
            proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            prefix.with_suffix(".log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
            if not report_path.is_file():
                raise RuntimeError(f"Slither created no report for {target}; inspect {prefix}.log")
            report = json.loads(report_path.read_text())
            if not report.get("success") or proc.returncode not in (0, 255):
                raise RuntimeError(f"Slither failed on {target}: {report.get('error')}")
            findings = report.get("results", {}).get("detectors", [])
            impacts = Counter(f["impact"] for f in findings)
            severe = impacts["High"] + impacts["Medium"]
            severe_count += severe
            run = {
                "group": group, "target": target,
                "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "command": command, "slither_exit_code": proc.returncode,
                "report": report_path.name, "counts": dict(impacts),
                "high_medium_count": severe,
                "findings": [{"check": f["check"], "impact": f["impact"], "confidence": f["confidence"],
                              "description": f["description"]} for f in findings],
            }
            summary["runs"].append(run)
            print(f"{group}: {target}: {dict(impacts)}")
    if any(hashlib.sha256((ROOT / target).read_bytes()).hexdigest() != digest
           for target, digest in source_hashes.items()):
        raise RuntimeError("Source changed during analysis; rerun on stable files")
    summary["high_medium_count"] = severe_count
    summary["exit_code"] = 1 if severe_count else 0
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Raw reports and summary: {out}")
    if severe_count:
        print("High/Medium findings remain in the raw report; consult STATIC_REVIEW.md for manual dispositions.")
    return summary["exit_code"]


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        print(f"Static analysis setup/tool error: {error}", file=sys.stderr)
        raise SystemExit(2)
