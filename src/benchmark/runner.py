# src/benchmark/runner.py
from __future__ import annotations
import json, logging, math, time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from circuits.base import BaseCircuit, CircuitRegistry
from core.compiler import Compiler, CompilerError
from core.prover import Prover, ProverError
from core.setup import Setup, SetupError
from core.verifier import Verifier, VerifierError

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkConfig:
    circuit_name: str
    circuit_path: Path
    iterations: int = 1
    ptau_power: Optional[int] = None
    seed: int = 42
    output_name: Optional[str] = None


@dataclass
class BenchmarkResult:
    config: BenchmarkConfig
    compile_time_s: float
    setup_time_s: float
    witness_time_s: float
    prove_time_s: float
    verify_time_s: float
    total_time_s: float
    constraints: int
    proof_size_bytes: int
    public_size_bytes: int
    peak_rss_mb: float
    success: bool
    error_stage: Optional[str] = None
    error_message: Optional[str] = None
    versions: Dict[str, str] = None
    timestamp: float = None


class BenchmarkError(RuntimeError):
    pass


def load_config_from_yaml(config_path: Path) -> List[BenchmarkConfig]:
    """Lightweight YAML loader for benchmark configs."""
    try:
        import yaml  # type: ignore
    except Exception as e:
        raise BenchmarkError("PyYAML is required: pip install pyyaml") from e

    data = yaml.safe_load(Path(config_path).read_text()) or {}
    bench = data.get("benchmark", {}) or {}
    defaults = {
        "iterations": int(bench.get("iterations", 1)),
        "ptau_power": bench.get("ptau_power"),
        "seed": int(bench.get("seed", 42)),
    }
    items = data.get("circuits", []) or []
    out: List[BenchmarkConfig] = []

    for it in items:
        file_val = it.get("file")
        if not file_val:
            raise BenchmarkError("Missing 'file' in circuits entry")
        p = Path(file_val)
        if not p.is_absolute():
            sc = Path("src") / "circuits" / p
            p = sc if sc.exists() else p

        cfg = BenchmarkConfig(
            circuit_name=it.get("name") or Path(file_val).stem,
            circuit_path=p,
            iterations=int(it.get("iterations", defaults["iterations"])),
            ptau_power=it.get("ptau_power", defaults["ptau_power"]),
            seed=int(it.get("seed", defaults["seed"])),
            output_name=it.get("output_name"),
        )
        out.append(cfg)
    return out


class BenchmarkRunner:
    def __init__(self, work_dir: Path, circom_bin: str = "circom", snarkjs_bin: str = "snarkjs", node_bin: str = "node"):
        self.work_dir = work_dir; self.work_dir.mkdir(parents=True, exist_ok=True)
        self.compiler = Compiler(circom_bin, snarkjs_bin)
        self.setup = Setup(snarkjs_bin, timeout_s=600, long_timeout_s=7200)
        self.prover = Prover(snarkjs_bin, node_bin)
        self.verifier = Verifier(snarkjs_bin)
        self.registry = CircuitRegistry()

    def run_single_benchmark(self, config: BenchmarkConfig, circuit: Optional[BaseCircuit] = None) -> BenchmarkResult:
        t0 = time.perf_counter()
        try:
            t_compile = time.perf_counter()
            comp = self.compiler.compile(config.circuit_path, self.work_dir / "build")
            compile_time = time.perf_counter() - t_compile

            constraints = int(comp.constraints)
            min_power = 8  # safe floor for small circuits
            auto_power = max(min_power, int(math.ceil(math.log2(max(2, constraints)))))
            chosen_power = auto_power if config.ptau_power is None else max(int(config.ptau_power), auto_power)

            t_setup = time.perf_counter()
            ptau = self.setup.ensure_ptau(self.work_dir / "ptau", chosen_power)
            sres = self.setup.groth16_setup(comp.r1cs, ptau, self.work_dir / "keys" / comp.circuit_name, circuit_name=comp.circuit_name)
            setup_time = time.perf_counter() - t_setup

            inputs_dir = self.work_dir / "inputs"; inputs_dir.mkdir(parents=True, exist_ok=True)
            input_file = inputs_dir / f"{config.circuit_name}_input.json"
            if circuit:
                data = circuit.generate_inputs(config.seed)
                circuit.write_inputs_json(data, input_file)
            else:
                if not input_file.exists():
                    raise BenchmarkError(f"No input file found and no circuit provided: {input_file}")

            t_prove = time.perf_counter()
            pres = self.prover.prove_with_witness_generation(
                comp.wasm, input_file, sres.zkey, self.work_dir / "proofs" / config.circuit_name, config.output_name or config.circuit_name
            )
            prove_time = time.perf_counter() - t_prove

            t_verify = time.perf_counter()
            vres = self.verifier.verify(sres.vkey_json, pres.public_json, pres.proof_json)
            verify_time = time.perf_counter() - t_verify

            total_time = time.perf_counter() - t0

            eff_config = BenchmarkConfig(
                circuit_name=config.circuit_name,
                circuit_path=config.circuit_path,
                iterations=1,
                ptau_power=chosen_power,
                seed=config.seed,
                output_name=config.output_name,
            )

            return BenchmarkResult(
                config=eff_config,
                compile_time_s=compile_time,
                setup_time_s=setup_time,
                witness_time_s=pres.witness_time_s,
                prove_time_s=pres.prove_time_s,
                verify_time_s=verify_time,
                total_time_s=total_time,
                constraints=comp.constraints,
                proof_size_bytes=pres.proof_size_bytes,
                public_size_bytes=pres.public_size_bytes,
                peak_rss_mb=pres.peak_rss_mb,
                success=vres.is_valid,
                versions=comp.versions,
                timestamp=time.time(),
            )

        except Exception as e:
            total_time = time.perf_counter() - t0
            es = "unknown"
            if isinstance(e, CompilerError) or "compile" in str(e).lower(): es = "compile"
            elif isinstance(e, SetupError) or "setup" in str(e).lower(): es = "setup"
            elif isinstance(e, ProverError) or "prove" in str(e).lower(): es = "prove"
            elif isinstance(e, VerifierError) or "verify" in str(e).lower(): es = "verify"
            eff_config = BenchmarkConfig(
                circuit_name=config.circuit_name,
                circuit_path=config.circuit_path,
                iterations=1,
                ptau_power=config.ptau_power,
                seed=config.seed,
                output_name=config.output_name,
            )
            return BenchmarkResult(
                config=eff_config,
                compile_time_s=0.0,
                setup_time_s=0.0,
                witness_time_s=0.0,
                prove_time_s=0.0,
                verify_time_s=0.0,
                total_time_s=total_time,
                constraints=0,
                proof_size_bytes=0,
                public_size_bytes=0,
                peak_rss_mb=0.0,
                success=False,
                error_stage=es,
                error_message=str(e),
                timestamp=time.time(),
            )

    def run_multiple_benchmarks(self, configs: List[BenchmarkConfig]) -> List[BenchmarkResult]:
        results: List[BenchmarkResult] = []
        for i, cfg in enumerate(configs):
            print(f"Running benchmark {i+1}/{len(configs)}: {cfg.circuit_name}")
            circ = self.registry.get_circuit(cfg.circuit_name)
            r = self.run_single_benchmark(cfg, circ)
            results.append(r)
            if r.success:
                print(f"  ✓ Success - {r.total_time_s:.2f}s total, {r.constraints} constraints")
            else:
                print(f"  ✗ Failed at {r.error_stage}: {r.error_message}")
        return results

    def run_benchmarks_with_iterations(self, configs: List[BenchmarkConfig]) -> List[BenchmarkResult]:
        all_results: List[BenchmarkResult] = []
        for cfg in configs:
            for it in range(cfg.iterations):
                logger.info(f"Running {cfg.circuit_name} iteration {it+1}/{cfg.iterations}")
                iter_cfg = BenchmarkConfig(
                    circuit_name=cfg.circuit_name,
                    circuit_path=cfg.circuit_path,
                    iterations=1,
                    ptau_power=cfg.ptau_power,
                    seed=cfg.seed + it,
                    output_name=f"{cfg.circuit_name}_iter_{it}",
                )
                circ = self.registry.get_circuit(cfg.circuit_name)
                all_results.append(self.run_single_benchmark(iter_cfg, circ))
        return all_results
    '''
    def save_results_jsonl(self, results: List[BenchmarkResult], output_file: Path) -> None:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            for r in results:
                f.write(json.dumps(asdict(r), default=str) + "\n")
    '''
    def save_results_jsonl(self, results: List[BenchmarkResult], output_file: Path, append: bool = False) -> None:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        # if append=True and file exists -> append, else overwrite
        mode = "a" if append and output_file.exists() else "w"
        with open(output_file, mode, encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps(asdict(r), default=str) + "\n")




    def load_results_jsonl(self, input_file: Path) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        with open(input_file, "r") as f:
            for line in f:
                if line.strip():
                    out.append(json.loads(line))
        return out

    def verify_tools(self) -> Dict[str, Any]:
        st: Dict[str, Any] = {}
        st.update(self.compiler.verify_tools())
        st.update(self.setup.verify_tools())
        st.update(self.prover.verify_tools())
        st.update(self.verifier.verify_tools())
        return st

    def get_summary_stats(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        if not results:
            return {"error": "No results provided"}
        succ = [r for r in results if r.success]
        fail = [r for r in results if not r.success]
        stats: Dict[str, Any] = {
            "total_runs": len(results),
            "successful_runs": len(succ),
            "failed_runs": len(fail),
            "success_rate": (len(succ) / len(results)) if results else 0.0,
        }
        if succ:
            tt = [r.total_time_s for r in succ]
            ct = [r.compile_time_s for r in succ]
            pt = [r.prove_time_s for r in succ]
            vt = [r.verify_time_s for r in succ]
            cons = [r.constraints for r in succ]
            ps = [r.proof_size_bytes for r in succ]
            stats["timing"] = {
                "total_time": {"mean": sum(tt)/len(tt), "min": min(tt), "max": max(tt)},
                "compile_time": {"mean": sum(ct)/len(ct), "min": min(ct), "max": max(ct)},
                "prove_time": {"mean": sum(pt)/len(pt), "min": min(pt), "max": max(pt)},
                "verify_time": {"mean": sum(vt)/len(vt), "min": min(vt), "max": max(vt)},
            }
            stats["circuit"] = {
                "constraints": {"mean": sum(cons)/len(cons), "min": min(cons), "max": max(cons)},
                "proof_size_bytes": {"mean": sum(ps)/len(ps), "min": min(ps), "max": max(ps)},
            }
        if fail:
            by_stage: Dict[str, int] = {}
            for r in fail:
                if r.error_stage:
                    by_stage[r.error_stage] = by_stage.get(r.error_stage, 0) + 1
            stats["failures"] = {"by_stage": by_stage, "sample_errors": [r.error_message for r in fail[:3]]}
        return stats
