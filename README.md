# zkSNARK Benchmark Framework

A comprehensive research framework for systematic performance evaluation of zero-knowledge proof circuits built with [Circom](https://docs.circom.io/) and [snarkjs](https://github.com/iden3/snarkjs). This framework implements the complete zk-SNARK workflow using the Groth16 protocol and provides detailed performance analytics across multiple circuit categories.

> **Research Use Only**: This framework is designed for academic research and educational purposes. Generated cryptographic keys and trusted setup parameters are not suitable for production deployment.

**PETs4DeFi participants: [task and input data](projects/pets4defi/README.md).**
This is the starting point for the economic analysis: measured operation costs,
privacy-cost comparisons against the cheapest tested signed option, missing inputs and the expected deliverable.
Implementation and reproduction instructions are in the
[technical experiment](examples/pets4defi_access_v2/README.md).

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Circuit Categories](#circuit-categories)
- [Usage Guide](#usage-guide)
- [Configuration](#configuration)
- [Performance Analysis](#performance-analysis)
- [Output Formats](#output-formats)
- [Troubleshooting](#troubleshooting)
- [Research Results](#research-results)
- [Limitations](#limitations)
- [Contributing](#contributing)
- [License](#license)

## Overview

This framework enables systematic benchmarking of zk-SNARK circuits across the complete proof lifecycle:

1. **Circuit Compilation**: Circom → R1CS constraint systems
2. **Trusted Setup**: Powers of Tau ceremony + circuit-specific setup
3. **Witness Generation**: Input processing through WebAssembly
4. **Proof Generation**: Groth16 proof creation with performance monitoring
5. **Verification**: Proof validation with timing measurements

The framework has been used to conduct comprehensive performance analysis across 8 representative circuit types, with results published in academic research demonstrating scaling characteristics from simple arithmetic (1 constraint) to complex cryptographic protocols (1.5M+ constraints).

## Features

### Core Capabilities
- **End-to-end automation**: Complete workflow from source circuits to verified proofs
- **Comprehensive metrics**: Timing, memory usage, constraint analysis, proof characteristics
- **Reproducible experiments**: Deterministic input generation with configurable seeds
- **Statistical rigor**: Multiple iterations with averaging and variance analysis
- **Cross-platform support**: Linux, macOS, Windows with PowerShell

### Performance Analysis
- **Scaling analysis**: Empirical validation of O(m log m) complexity
- **Resource profiling**: Memory consumption tracking and optimization
- **Comparative benchmarking**: Performance across different circuit categories
- **Regression analysis**: Statistical modeling of performance characteristics
- **Export capabilities**: CSV, JSON, and markdown report generation

### Circuit Support
- **Arithmetic operations**: Basic field arithmetic and polynomial evaluation
- **Cryptographic primitives**: Hash functions (Poseidon, MiMC), range proofs
- **Structural proofs**: Merkle tree membership with configurable depth
- **Advanced cryptography**: ECDSA signature verification (secp256k1)

## Requirements

### Software Dependencies
- **Python** ≥ 3.10 with development headers
- **Node.js** ≥ 18.0 (tested with 22.x)
- **Circom** 2.1.x compiler (available on system PATH)
- **snarkjs** library (globally installed via npm)

### System Requirements
- **Memory**: Minimum 8GB RAM (16GB+ recommended for ECDSA circuits)
- **Storage**: 5GB+ free space for artifacts and intermediate files
- **CPU**: Modern multi-core processor (benchmarks are CPU-intensive)

### Platform-Specific Notes
- **Linux/macOS**: Bash shell with standard POSIX utilities
- **Windows**: PowerShell 5.0+ (cmd.exe not supported)
- **Memory-intensive circuits**: May require Node.js heap size adjustment

## Installation

### 1. Repository Setup
```bash
# Clone with submodules (includes ECDSA circuit dependencies)
git clone https://github.com/KuznetsovKarazin/zksnark-benchmark
cd zksnark-benchmark
git submodule update --init --recursive
```

### 2. Python Environment
```bash
# Create isolated environment
python -m venv venv

# Activate environment
# Linux/macOS:
source venv/bin/activate
# Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Node.js Dependencies
```bash
# Install local project dependencies
npm install

# Install snarkjs globally
npm install -g snarkjs

# Verify installation
snarkjs --version
```

### 4. Circom Installation

**Option A: Package Managers**
```bash
# Ubuntu/Debian
sudo apt install circom

# macOS with Homebrew
brew install circom

# Arch Linux
sudo pacman -S circom
```

**Option B: From Source**
```bash
git clone https://github.com/iden3/circom.git
cd circom
cargo build --release
cargo install --path circom
```

### 5. Verification
```bash
# Verify all tools are available
python run_benchmark.py --verify-tools

# Expected output:
# Tool Status:
# ========================================
# ✓ circom: circom compiler 2.1.9 (/usr/local/bin/circom)
# ✓ snarkjs: snarkjs@0.7.4 (/usr/local/bin/snarkjs) 
# ✓ node: v22.19.0 (/usr/local/bin/node)
```

## Quick Start

### Basic Circuit Benchmark
```bash
# Simple multiplication circuit
python run_benchmark.py --circuit src/circuits/basic/multiply.circom

# With multiple iterations for statistical accuracy
python run_benchmark.py --circuit src/circuits/basic/multiply.circom --iterations 10
```

### Cryptographic Primitives
```bash
# Poseidon hash function
python run_benchmark.py --circuit src/circuits/crypto/poseidon_hash.circom --iterations 5

# Merkle proof (requires input generation)
node scripts/gen_merkle_poseidon.js 16 0 > data/benchmarks/inputs/merkle_poseidon_input.json
python run_benchmark.py --circuit src/circuits/crypto/merkle_poseidon.circom
```

### Complete Benchmark Suite
```bash
# Run comprehensive benchmark across all circuit types
python run_benchmark.py --config config/benchmark.yaml

# Append results to existing data
python run_benchmark.py --config config/benchmark.yaml --append
```

### Analysis and Reporting
```bash
# Generate comprehensive performance analysis
python scripts/analyze_results.py --input data/benchmarks/results.jsonl

# Output: CSV files, charts, and markdown report in docs/reports/
```

## Project Structure

```
zksnark-benchmark/
├── src/                           # Source code
│   ├── core/                      # Core framework components
│   │   ├── compiler.py           # Circom compilation with R1CS analysis
│   │   ├── setup.py              # Trusted setup and PTAU management  
│   │   ├── prover.py             # Witness generation and proof creation
│   │   └── verifier.py           # Proof verification with timing
│   ├── circuits/                  # Circuit implementations
│   │   ├── base.py               # Circuit registry and input generators
│   │   ├── basic/                # Simple arithmetic circuits
│   │   │   ├── multiply.circom   # Basic multiplication
│   │   │   ├── quadratic.circom  # Quadratic polynomial evaluation
│   │   │   └── range_proof.circom # Range proof via bit decomposition
│   │   └── crypto/               # Cryptographic primitives
│   │       ├── poseidon_hash.circom    # Poseidon hash function
│   │       ├── hash.circom             # MiMC-sponge hash
│   │       ├── merkle_poseidon.circom  # Merkle tree membership
│   │       └── ecdsa_verify.circom     # ECDSA signature verification
│   └── benchmark/
│       └── runner.py             # Main benchmarking orchestration
├── scripts/                       # Utilities and generators
│   ├── gen_merkle_poseidon.js    # Merkle proof input generator
│   ├── gen_ecdsa.js              # ECDSA test vector generator
│   └── analyze_results.py        # Statistical analysis and reporting
├── config/                        # Experiment configurations
│   ├── benchmark.yaml            # Complete benchmark suite
│   ├── minimal.yaml              # Quick validation tests
│   └── extended.yaml             # Extended research configuration
├── vendor/                        # External dependencies
│   └── circom-ecdsa/             # ECDSA circuit library (submodule)
├── data/                          # Working directory (git-ignored)
│   └── benchmarks/
│       ├── results.jsonl         # Accumulated benchmark results
│       ├── metadata.json         # Environment and tool information
│       ├── build/                # Compilation artifacts (R1CS, WASM)
│       ├── keys/                 # Cryptographic keys (zkey, vkey)
│       ├── proofs/               # Generated proofs and witnesses
│       ├── inputs/               # Test input JSON files
│       └── ptau/                 # Powers of Tau ceremony files
├── docs/                          # Documentation and reports
│   └── reports/                  # Generated analysis reports
├── tests/                         # Unit and integration tests
├── run_benchmark.py              # Main CLI interface
├── requirements.txt              # Python dependencies
├── package.json                  # Node.js dependencies
└── README.md                     # This file
```

## Circuit Categories

### 1. Arithmetic Circuits
**Purpose**: Baseline performance measurement and overhead analysis

- **multiply.circom**: Basic field multiplication (1 constraint)
- **quadratic.circom**: Polynomial evaluation y = ax² + bx + c (3 constraints)

**Use cases**: Simple validation, overhead measurement, regression testing

### 2. Range Proofs
**Purpose**: Demonstrate bit decomposition and boolean constraints

- **range_proof.circom**: Prove 0 ≤ x < 2³² using Num2Bits (32 constraints)

**Use cases**: Age verification, balance proofs, threshold validation

### 3. Cryptographic Hash Functions
**Purpose**: Evaluate efficiency of cryptographic primitives in R1CS

- **hash.circom**: MiMC-sponge with 220 rounds (1,320 constraints)
- **poseidon_hash.circom**: Poseidon hash optimized for zk-SNARKs (240 constraints)

**Use cases**: Commitment schemes, nullifiers, private state transitions

### 4. Merkle Tree Proofs
**Purpose**: Assess structured data verification performance

- **merkle_poseidon.circom**: Binary Merkle tree with configurable depth
  - Depth 4: ~980 constraints (16 leaves)
  - Depth 16: ~3,890 constraints (65,536 leaves)

**Use cases**: Set membership, blockchain inclusion proofs, private voting

### 5. Digital Signature Verification
**Purpose**: Complex cryptographic protocol implementation

- **ecdsa_verify.circom**: secp256k1 ECDSA verification (1,510,185 constraints)

**Use cases**: Anonymous authentication, private key proofs, cross-chain verification

## Usage Guide

### Command Line Interface

```bash
# Basic usage
python run_benchmark.py [OPTIONS]

# Options:
--circuit PATH              # Single circuit file to benchmark
--config PATH               # YAML configuration file
--iterations N              # Number of test iterations (default: 1)
--ptau-power N              # Override Powers of Tau size
--workdir PATH              # Working directory (default: data/benchmarks)
--append                    # Append to existing results
--verify-tools              # Check tool availability and exit
--verbose                   # Enable detailed logging
--timeout SECONDS           # Maximum execution time per circuit
```

### Single Circuit Benchmarking

```bash
# Basic arithmetic with timing
python run_benchmark.py --circuit src/circuits/basic/multiply.circom --iterations 10

# Cryptographic primitive with memory monitoring
python run_benchmark.py --circuit src/circuits/crypto/poseidon_hash.circom --iterations 5

# Complex circuit with custom PTAU power
python run_benchmark.py --circuit src/circuits/crypto/ecdsa_verify.circom --ptau-power 21
```

### Input Data Generation

The framework includes specialized generators for complex circuits:

```bash
# Merkle tree proofs
node scripts/gen_merkle_poseidon.js <depth> <leaf_index> [seed]
# Example: depth=16, leaf_index=5, seed=42
node scripts/gen_merkle_poseidon.js 16 5 42 > data/benchmarks/inputs/merkle_poseidon_input.json

# ECDSA signatures  
node scripts/gen_ecdsa.js [seed]
# Example: deterministic test with seed=123
node scripts/gen_ecdsa.js 123 > data/benchmarks/inputs/ecdsa_verify_input.json
```

### Memory Configuration

For memory-intensive circuits (particularly ECDSA):

```bash
# Linux/macOS
export NODE_OPTIONS="--max-old-space-size=16384"
python run_benchmark.py --circuit src/circuits/crypto/ecdsa_verify.circom

# Windows PowerShell
$env:NODE_OPTIONS="--max-old-space-size=16384"
python run_benchmark.py --circuit src/circuits/crypto/ecdsa_verify.circom
```

## Configuration

### YAML Configuration Schema

```yaml
benchmark:
  iterations: 3                    # Default iterations per circuit
  seed: 42                        # Base seed for reproducibility
  timeout_s: 1800                 # Maximum time per circuit (seconds)
  ptau_power: null                # Global PTAU override (optional)

circuits:
  - name: "multiply"              # Unique identifier
    file: "basic/multiply.circom" # Path relative to src/circuits/
    iterations: 10                # Override default iterations
    ptau_power: 8                 # Override PTAU power (optional)
    description: "Basic multiplication"  # Optional documentation
    
  - name: "poseidon_hash"
    file: "crypto/poseidon_hash.circom"
    iterations: 5
    description: "Poseidon hash function optimized for zk-SNARKs"
```

### Example Configurations

**Quick Validation** (`config/minimal.yaml`):
```yaml
benchmark:
  iterations: 1
  timeout_s: 300

circuits:
  - name: "multiply"
    file: "basic/multiply.circom"
  - name: "quadratic" 
    file: "basic/quadratic.circom"
```

**Research Suite** (`config/benchmark.yaml`):
```yaml
benchmark:
  iterations: 10
  seed: 42
  timeout_s: 3600

circuits:
  - name: "multiply"
    file: "basic/multiply.circom"
    iterations: 10
  - name: "ecdsa_verify"
    file: "crypto/ecdsa_verify.circom"
    iterations: 3
    ptau_power: 21
```

## Performance Analysis

### Metrics Collected

**Timing Metrics** (microsecond precision):
- Compilation time: Circom → R1CS + WASM
- Setup time: Trusted setup key generation
- Witness time: Input processing and constraint evaluation
- Prove time: zk-SNARK proof generation
- Verify time: Proof validation
- Total time: End-to-end execution

**Resource Metrics**:
- Peak memory usage (RSS)
- Constraint count (R1CS system size)
- Proof size (bytes)
- Public input size (bytes)

**Quality Metrics**:
- Success/failure rates
- Error categorization
- Tool version tracking
- Environment metadata

### Statistical Analysis

The analysis script provides comprehensive statistical evaluation:

```bash
python scripts/analyze_results.py --input data/benchmarks/results.jsonl [options]

# Options:
--output-dir PATH           # Output directory (default: docs/reports/timestamp)
--format {csv,json,md}     # Output formats
--include-charts           # Generate performance charts
--regression-analysis      # Perform scaling analysis
```

**Generated Reports**:
- `raw_results.csv`: Per-execution data
- `summary_by_circuit.csv`: Aggregated statistics
- `scaling_analysis.csv`: Regression coefficients
- `performance_charts/`: Visualization suite
- `report.md`: Human-readable analysis

### Scaling Analysis

The framework performs empirical validation of theoretical complexity:

- **Regression fitting**: log(time) vs log(constraints)
- **Goodness of fit**: R² coefficient analysis
- **Complexity validation**: Comparison with O(m log m) theoretical bound
- **Outlier detection**: Statistical anomaly identification

## Output Formats

### JSON Lines Results
Each benchmark execution produces a structured record:

```json
{
  "config": {
    "circuit_name": "poseidon_hash",
    "circuit_path": "src/circuits/crypto/poseidon_hash.circom",
    "iterations": 1,
    "ptau_power": 8,
    "seed": 42
  },
  "compile_time_s": 0.009,
  "setup_time_s": 0.0004,
  "witness_time_s": 0.101,
  "prove_time_s": 0.721,
  "verify_time_s": 0.630,
  "total_time_s": 1.464,
  "constraints": 240,
  "proof_size_bytes": 807,
  "public_size_bytes": 84,
  "peak_rss_mb": 123.06,
  "success": true,
  "error_stage": null,
  "error_message": null,
  "versions": {
    "circom": "circom compiler 2.1.9",
    "snarkjs": "snarkjs@0.7.4",
    "node": "v22.19.0"
  },
  "timestamp": 1703123456.789
}
```

### Environment Metadata
System and tool information for reproducibility:

```json
{
  "tools": {
    "circom": {"available": true, "version": "2.1.9", "path": "/usr/local/bin/circom"},
    "snarkjs": {"available": true, "version": "0.7.4", "path": "/usr/local/bin/snarkjs"},
    "node": {"available": true, "version": "v22.19.0", "path": "/usr/local/bin/node"}
  },
  "env": {
    "timestamp": 1703123456.0,
    "host": "research-server",
    "python": "3.10.8",
    "os": "Linux-5.15.0-generic-x86_64",
    "cpu_count": 16,
    "ram_total_gb": 32.0
  }
}
```

## Troubleshooting

### Common Issues

**`snarkjs: command not found`**
```bash
# Install globally
npm install -g snarkjs
# Verify installation
which snarkjs
snarkjs --version
```

**`circom: command not found`**
```bash
# Add to PATH (Linux/macOS)
export PATH=$PATH:/path/to/circom
# Windows PowerShell
$env:PATH += ";C:\path\to\circom"
```

**Memory errors during witness generation**
```bash
# Increase Node.js heap size
export NODE_OPTIONS="--max-old-space-size=16384"
# For extremely large circuits, use 32GB
export NODE_OPTIONS="--max-old-space-size=32768"
```

**`Invalid file format` during key export**
```bash
# PTAU file too small for circuit
# Framework auto-detects size, but manual override:
python run_benchmark.py --circuit path/to/circuit.circom --ptau-power 20
```

**Windows path separator issues**
```bash
# Use PowerShell, not cmd.exe
# Verify Python path resolution
python -c "import pathlib; print(pathlib.Path('src/circuits/basic/multiply.circom').exists())"
```

### Performance Optimization

**For faster iterations**:
- Pre-generate large PTAU files
- Use SSD storage for working directory
- Increase system memory for parallel processing

**For memory-constrained systems**:
- Skip ECDSA circuit (1.5M+ constraints)
- Reduce Merkle tree depth
- Use `--timeout` to prevent runaway processes

### Debug Mode

```bash
# Enable verbose logging
python run_benchmark.py --circuit path/to/circuit.circom --verbose

# Check intermediate artifacts
ls -la data/benchmarks/build/circuit_name/
# Should contain: circuit.r1cs, circuit.wasm, circuit.sym
```

## Research Results

This framework has been used to conduct systematic performance analysis across multiple circuit categories, yielding several key findings:

### Empirical Validation
- **Scaling Complexity**: Confirmed O(m log m) scaling with R² = 0.987
- **Proof Size Stability**: Constant ~805 bytes regardless of circuit complexity
- **Verification Consistency**: ~0.66s verification time across all circuits

### Performance Benchmarks
Circuit class performance (normalized per 1K constraints):

| Category | Time/1K constraints | Memory efficiency | Economic cost |
|----------|-------------------|------------------|---------------|
| Arithmetic | 21-690 seconds | Poor | $0.001-0.019 |
| Cryptographic | 0.6-3.0 seconds | Good | $0.020-0.022 |
| Structural | 0.2-0.8 seconds | Excellent | $0.021-0.042 |
| Advanced | 0.022 seconds | Optimal | $5.577 |

### Statistical Validation
- **Coefficient of variation**: <5% for timing metrics
- **Memory stability**: 0.56% variance across circuit types  
- **Proof size consistency**: 0.21% variance (highly stable)

## Limitations

### Experimental Limitations
- **Statistical power**: Results based on 1-10 iterations per circuit
- **Platform dependency**: Benchmarks conducted on specific hardware configuration
- **Single protocol**: Framework currently supports Groth16 only
- **Measurement granularity**: Limited by system timer resolution

### Technical Constraints  
- **Trusted setup**: Generated keys suitable for research only
- **Memory requirements**: Large circuits require substantial RAM
- **Compilation time**: Complex circuits may require extended compilation
- **Tool dependencies**: Requires specific versions of external tools

### Scope Limitations
- **Circuit coverage**: Representative sample, not exhaustive
- **Input variety**: Limited test vector diversity per circuit
- **Network effects**: No analysis of distributed proving/verification
- **Hardware specificity**: Results may not generalize across architectures

## Contributing

### Research Collaboration
This framework is designed to facilitate reproducible zk-SNARK research. Contributions should maintain scientific rigor:

- **Reproducibility**: Include complete environment specifications
- **Documentation**: Provide detailed circuit analysis and complexity bounds
- **Validation**: Include test vectors and expected results
- **Statistical rigor**: Support claims with appropriate statistical analysis

### Code Contributions
When contributing new circuits or functionality:

1. **Circuit implementation**: Follow existing patterns in `src/circuits/`
2. **Input generators**: Provide deterministic test data generators
3. **Documentation**: Include complexity analysis and use cases
4. **Testing**: Add comprehensive test coverage
5. **Benchmarking**: Validate performance characteristics

### Adding New Circuits

```python
# 1. Implement circuit in src/circuits/category/
# 2. Add to circuit registry in src/circuits/base.py

class NewCircuit(BaseCircuit):
    def __init__(self):
        super().__init__(name="new_circuit", description="...")
    
    def generate_inputs(self, seed=None):
        # Return dict of inputs for circuit
        pass
    
    def get_expected_constraints(self):
        # Return estimated constraint count
        pass
    
    def _get_required_signals(self):
        # Return list of required input signals
        pass

# 3. Register in CircuitRegistry
registry.register(NewCircuit())
```

## Security Notice

**Critical**: All cryptographic material generated by this framework is for research and educational purposes only. 

- **Keys**: Never use generated proving/verification keys in production
- **PTAU**: Trusted setup parameters are not secure for real applications  
- **Proofs**: Generated proofs provide no security guarantees
- **Circuits**: Implementations may contain vulnerabilities

For production deployment, use properly audited circuits and participate in secure multi-party trusted setup ceremonies.

## License

MIT License - see [LICENSE](LICENSE) file for complete terms.

## Citation

If you use this framework in academic research, please cite:

```bibtex
@misc{zksnark-benchmark-2025,
  title={zkSNARK Benchmark Framework: Systematic Performance Evaluation of Zero-Knowledge Proof Circuits},
  author={Kuznetsov, Oleksandr},
  year={2025},
  howpublished={\url{https://github.com/KuznetsovKarazin/zksnark-benchmark}},
  note={Research framework for zk-SNARK circuit benchmarking}
}
```

## Acknowledgments

This framework builds upon:
- [Circom](https://docs.circom.io/) circuit compiler
- [snarkjs](https://github.com/iden3/snarkjs) proof system library
- [circomlib](https://github.com/iden3/circomlib) circuit library
- [circom-ecdsa](https://github.com/0xPARC/circom-ecdsa) ECDSA circuits

---

**Repository**: https://github.com/KuznetsovKarazin/zksnark-benchmark  
**Documentation**: Complete API reference and examples in `docs/`  
**Issues**: Bug reports and feature requests welcome on GitHub
