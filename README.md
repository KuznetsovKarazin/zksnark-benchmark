# zksnark-benchmark

A modular, batteries-included framework to **compile, prove, verify, and benchmark** [Circom](https://docs.circom.io/) circuits using **snarkjs (Groth16)** — with **auto PTAU sizing**, **caching**, and a **report generator** (CSV + charts + Markdown).

> Built for research and education: quick iteration on circuits from “toy” arithmetic to heavy crypto (Poseidon, Merkle, ECDSA), stable metrics, and reproducible results.

---

## Highlights

- **End-to-end pipeline**: compile → setup → witness → prove → verify  
- **Auto PTAU sizing** from R1CS (`ceil(log2(constraints))`, with a safe floor)  
- **Phase 2 skip**: if `powersOfTau28_hez_final_<p>.ptau` exists → **no** `prepare phase2`  
- **Resilient proving**: witness with Node WASM; metrics captured for each stage  
- **Analytics**: one command to build CSVs, charts (matplotlib), and a Markdown report  
- **Vendor crypto**: ECDSA circuits via git submodule (`vendor/circom-ecdsa`)  
- **Config-driven**: run suites from YAML and **append** results to JSONL

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Running Benchmarks](#running-benchmarks)
  - [Single Circuit](#single-circuit)
  - [Benchmark Suite (YAML)](#benchmark-suite-yaml)
  - [ECDSA (Heavy)](#ecdsa-heavy)
- [Analytics & Reports](#analytics--reports)
- [Configuration Reference](#configuration-reference)
- [Design Notes](#design-notes)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
- [License](#license)

---

## Requirements

- **Python** ≥ 3.10  
- **Node.js** ≥ 18 (tested with 22.x)  
- **circom** 2.1.x (available on `PATH`)  
- **snarkjs** (global)
- OS: Linux / macOS / Windows (PowerShell)

**Node packages (local project):**
- `circomlib`, `ffjavascript`, `secp256k1`

> For very large witnesses (e.g., ECDSA), increase Node memory:  
> Linux/macOS: `export NODE_OPTIONS="--max-old-space-size=16384"`  
> Windows PowerShell: `$env:NODE_OPTIONS="--max-old-space-size=16384"`

---

## Installation

```bash
# 1) Clone and pull submodules (ECDSA vendor)
git clone <YOUR_REPO_URL> zksnark-benchmark
cd zksnark-benchmark
git submodule update --init --recursive

# 2) Python environment
python -m venv venv
# Linux/macOS:
source venv/bin/activate
# Windows PowerShell:
# .\venv\Scripts\Activate.ps1
pip install -r requirements.txt  # or: pip install -e . (if pyproject.toml exists)

# 3) Node dependencies (local) and snarkjs (global)
npm i -S circomlib ffjavascript secp256k1
npm i -g snarkjs

# 4) Sanity check
python run_benchmark.py --verify-tools
```

> Install `circom` from official sources or package managers; ensure `circom --version` returns 2.1.x.

---

## Project Structure

```
zksnark-benchmark/
├─ src/
│  ├─ core/
│  │  ├─ compiler.py        # Circom compile, include paths, constraints detection
│  │  ├─ setup.py           # PTAU management, Groth16 setup (skip phase2 if final PTAU present)
│  │  ├─ prover.py          # Witness generation (Node WASM) + prove (snarkjs)
│  │  └─ verifier.py        # Verify proofs (snarkjs)
│  ├─ circuits/
│  │  ├─ basic/
│  │  │  └─ multiply.circom
│  │  ├─ crypto/
│  │  │  ├─ poseidon_hash.circom
│  │  │  ├─ merkle_poseidon.circom
│  │  │  └─ ecdsa_verify.circom
│  │  └─ base.py            # Circuit registry & helpers (inputs, paths)
│  └─ benchmark/
│     └─ runner.py          # BenchmarkRunner, auto-PTAU, JSONL saving, stats
├─ scripts/
│  ├─ gen_merkle_poseidon.js  # Input generator (Merkle+Poseidon)
│  ├─ gen_ecdsa.js            # Input generator (ECDSA), outputs expect_ok=1
│  └─ analyze_results.py      # CSV + charts + report.md
├─ config/
│  ├─ benchmark-suite.yaml    # Example suite (multiply, poseidon, merkle, ecdsa)
│  └─ *.yaml                  # Other configs (dev/ci)
├─ vendor/
│  └─ circom-ecdsa/           # Git submodule (ECDSA circuits)
├─ docs/
│  └─ reports/                # Generated reports (CSV, PNG, Markdown)
├─ data/                      # Workdir (ignored by git)
│  └─ benchmarks/
│     ├─ ptau/                # PTAU files (final + generated)
│     ├─ build/               # circom outputs (r1cs/wasm/sym)
│     ├─ keys/                # zkey/vkey
│     ├─ proofs/              # proof.json/public.json/wtns
│     ├─ inputs/              # input JSONs
│     ├─ results.jsonl        # accumulated benchmark results
│     └─ metadata.json        # tool versions & environment snapshot
├─ run_benchmark.py           # CLI to run single or suite benchmarks
├─ pytest.ini / tests/        # Unit tests
├─ .gitignore
└─ README.md / LICENSE
```

---

## Quick Start

**Single circuit (toy):**
```bash
python run_benchmark.py --circuit src/circuits/basic/multiply.circom --iterations 1
```

**Poseidon hash:**
```bash
python run_benchmark.py --circuit src/circuits/crypto/poseidon_hash.circom --iterations 1
```

**Merkle+Poseidon (needs input json):**
```bash
node scripts/gen_merkle_poseidon.js 16 5 > data/benchmarks/inputs/merkle_poseidon_input.json
python run_benchmark.py --circuit src/circuits/crypto/merkle_poseidon.circom --iterations 1
```

---

## Running Benchmarks

### Single Circuit

```bash
python run_benchmark.py   --circuit src/circuits/crypto/poseidon_hash.circom   --iterations 3
```

**Options:**
- `--iterations N` — repeat runs (seeds auto-increment)
- `--ptau-power P` — override PTAU power (otherwise auto from constraints)
- `--workdir PATH` — work directory (default: `data/benchmarks`)
- `--append` — append results to the existing `results.jsonl` (instead of overwriting)
- `--verify-tools` — print tool availability (circom/snarkjs/node) and exit

> **Auto PTAU**: after compile, the runner computes `ceil(log2(constraints))`  
> with a safe minimum power (8). If a **final PTAU** file  
> `data/benchmarks/ptau/powersOfTau28_hez_final_<P>.ptau` exists, **phase2 is skipped**.

### Benchmark Suite (YAML)

`config/benchmark-suite.yaml` (example):
```yaml
benchmark:
  iterations: 3
  seed: 42

circuits:
  - name: "multiply"
    file: "basic/multiply.circom"

  - name: "poseidon_hash"
    file: "crypto/poseidon_hash.circom"

  - name: "merkle_poseidon"
    file: "crypto/merkle_poseidon.circom"

  - name: "ecdsa_verify"
    file: "crypto/ecdsa_verify.circom"
```

Run the suite:
```bash
python run_benchmark.py --config config/benchmark-suite.yaml --append
```

### ECDSA (Heavy)

1) Download **final PTAU** for `2^21` to skip heavy `prepare phase2`:

```
data/benchmarks/ptau/powersOfTau28_hez_final_21.ptau
```

2) Generate inputs:
```bash
node scripts/gen_ecdsa.js 123 > data/benchmarks/inputs/ecdsa_verify_input.json
```

3) Increase Node memory (optional but recommended):
```bash
# Linux/macOS
export NODE_OPTIONS="--max-old-space-size=16384"
# Windows PowerShell
# $env:NODE_OPTIONS="--max-old-space-size=16384"
```

4) Run:
```bash
python run_benchmark.py --circuit src/circuits/crypto/ecdsa_verify.circom --iterations 1
```

---

## Analytics & Reports

After accumulating results in `data/benchmarks/results.jsonl`:

```bash
pip install pandas matplotlib
python scripts/analyze_results.py --input data/benchmarks/results.jsonl
```

Outputs → `docs/reports/<timestamp>/`:
- `raw_results.csv` — per-run data
- `summary_overall.csv`, `summary_by_circuit.csv`
- `time_vs_constraints_*.png`, `proofsize_vs_constraints.png`, `time_breakdown_stacked.png`
- `scaling_fit.csv` & `scaling_alpha.txt` (log-log regression: `time ≈ k * constraints^α`)
- `report.md` — human-readable summary with inline charts

---

## Configuration Reference

YAML schema (minimal):

```yaml
benchmark:
  iterations: 1        # default iterations for circuits
  seed: 42             # base seed (incremented per iteration)
  ptau_power: null     # optional global override

circuits:
  - name: "poseidon_hash"
    file: "crypto/poseidon_hash.circom"
    iterations: 3      # per-circuit override
    ptau_power: 10     # per-circuit override (if provided, runner uses max(auto, this))
    output_name: null  # optional different basename for outputs
```

---

## Design Notes

- **Separation of concerns**: `core` (tools) vs. `benchmark` (orchestration) vs. `scripts` (I/O + analytics).
- **Reproducibility**: `results.jsonl` + `metadata.json` (tools & environment snapshot).
- **Extensibility**: register new circuits in `src/circuits/base.py` (or pass custom inputs via `data/benchmarks/inputs/*.json`).
- **Safety**: enforces `expect_ok` where applicable (e.g., ECDSA), skips `prepare phase2` for final PTAU.

> **Trusted Setup**: Groth16 keys are for **research only**. Never reuse these keys for production deployments.

---

## Troubleshooting

**`Invalid File format` during `zkey export verificationkey`**  
PTAU too small for the circuit. The runner auto-sizes; if overriding manually, use a sufficient `--ptau-power`. Safe floor is 8; ECDSA typically needs **21**.

**`Non quadratic constraints are not allowed!`**  
Your Circom code contains non-quadratic constraints; refactor to R1CS-compatible form (e.g., avoid ternaries on signals by using mux components).

**`include not found` (`circomlib/...`)**  
Include directories are passed as `-l src/circuits -l node_modules -l vendor/circom-ecdsa/circuits`. Ensure dependencies exist.

**Witness generation fails with BigInt / memory errors**  
Increase Node heap:
- Linux/macOS: `export NODE_OPTIONS="--max-old-space-size=16384"`
- Windows PowerShell: `$env:NODE_OPTIONS="--max-old-space-size=16384"`

**Windows path issues**  
Prefer PowerShell. Remove caches with:  
`Remove-Item -Recurse -Force src\**\__pycache__ .pytest_cache`

---

## Roadmap

- Optional PLONK backend for large circuits (no Powers of Tau)  
- HTML report renderer (from Markdown)  
- More crypto circuits and parameterized suites  
- CLI subcommands for report generation and artifact cleanup

---

## License

[MIT](LICENSE)
