"""
Prover module for zkSNARK Benchmark Framework.

Handles witness generation and proof creation with performance profiling.
Tracks memory usage, timing, and proof sizes for benchmarking purposes.
"""

from __future__ import annotations

import json
import platform
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


@dataclass
class ProveResult:
    """Result of proof generation process."""
    witness: Path
    proof_json: Path
    public_json: Path
    witness_time_s: float
    prove_time_s: float
    peak_rss_mb: float
    proof_size_bytes: int
    public_size_bytes: int


class ProverError(RuntimeError):
    """Proof generation error."""
    pass


class Prover:
    """Witness generation and proof creation with profiling."""
    
    def __init__(
        self, 
        snarkjs_bin: str = "snarkjs",
        node_bin: str = "node",
        timeout_s: int = 600
    ):
        """Initialize prover with tool paths.
        
        Args:
            snarkjs_bin: Path to snarkjs binary
            node_bin: Path to node binary  
            timeout_s: Timeout for proof commands
        """
        self.snarkjs_bin = snarkjs_bin
        self.node_bin = node_bin
        self.timeout_s = timeout_s
        self.use_shell = platform.system() == "Windows"
        self._last_command_time = 0.0

    def generate_witness(
        self, 
        wasm: Path, 
        input_json: Path, 
        out_wtns: Path
    ) -> float:
        """Generate witness from circuit WASM and inputs.
        
        Args:
            wasm: Path to circuit WASM file
            input_json: Path to input JSON file
            out_wtns: Output path for witness file
            
        Returns:
            Witness generation time in seconds
            
        Raises:
            ProverError: If witness generation fails
        """
        if not wasm.exists():
            raise ProverError(f"WASM file not found: {wasm}")
        if not input_json.exists():
            raise ProverError(f"Input file not found: {input_json}")
        
        # Locate witness generator - different circom versions use different paths
        gen_js = wasm.parent / "generate_witness.js"
        if not gen_js.exists():
            # Try alternative path for newer circom versions
            gen_js = wasm.parent / f"{wasm.stem}_js" / "generate_witness.js"
        
        if not gen_js.exists():
            raise ProverError(f"Witness generator not found near {wasm}")
        
        out_wtns.parent.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            self.node_bin, str(gen_js), 
            str(wasm), str(input_json), str(out_wtns)
        ]
        
        t0 = time.perf_counter()
        self._run(cmd)
        witness_time = time.perf_counter() - t0
        
        if not out_wtns.exists():
            raise ProverError(f"Witness file not generated: {out_wtns}")
        
        return witness_time

    def prove(
        self, 
        zkey: Path, 
        wtns: Path, 
        out_dir: Path,
        circuit_name: Optional[str] = None
    ) -> ProveResult:
        """Generate Groth16 proof from witness and proving key.
        
        Args:
            zkey: Path to proving key file
            wtns: Path to witness file
            out_dir: Output directory for proof files
            circuit_name: Name for output files
            
        Returns:
            ProveResult with timing and size metrics
            
        Raises:
            ProverError: If proof generation fails
        """
        if not zkey.exists():
            raise ProverError(f"Proving key not found: {zkey}")
        if not wtns.exists():
            raise ProverError(f"Witness file not found: {wtns}")
        
        out_dir.mkdir(parents=True, exist_ok=True)
        name = circuit_name or zkey.stem
        
        proof_json = out_dir / f"{name}_proof.json"
        public_json = out_dir / f"{name}_public.json"
        
        # Memory profiling setup
        initial_rss = self._get_memory_usage()
        
        cmd = [
            self.snarkjs_bin, "groth16", "prove",
            str(zkey), str(wtns), str(proof_json), str(public_json)
        ]
        
        t0 = time.perf_counter()
        self._run(cmd)
        prove_time = time.perf_counter() - t0
        
        # Memory usage estimation (basic)
        final_rss = self._get_memory_usage()
        peak_rss_mb = max(initial_rss, final_rss)
        
        if not proof_json.exists():
            raise ProverError(f"Proof file not generated: {proof_json}")
        if not public_json.exists():
            raise ProverError(f"Public inputs file not generated: {public_json}")
        
        # Collect file sizes
        proof_size = proof_json.stat().st_size
        public_size = public_json.stat().st_size
        
        return ProveResult(
            witness=wtns,
            proof_json=proof_json,
            public_json=public_json,
            witness_time_s=0.0,  # Set externally
            prove_time_s=prove_time,
            peak_rss_mb=peak_rss_mb,
            proof_size_bytes=proof_size,
            public_size_bytes=public_size
        )

    def prove_with_witness_generation(
        self,
        wasm: Path,
        input_json: Path,
        zkey: Path,
        out_dir: Path,
        circuit_name: Optional[str] = None
    ) -> ProveResult:
        """Complete prove workflow: generate witness + create proof.
        
        Args:
            wasm: Path to circuit WASM file
            input_json: Path to input JSON file
            zkey: Path to proving key file
            out_dir: Output directory for all files
            circuit_name: Name for output files
            
        Returns:
            ProveResult with complete timing metrics
        """
        out_dir.mkdir(parents=True, exist_ok=True)
        name = circuit_name or wasm.stem
        
        # Generate witness
        wtns = out_dir / f"{name}.wtns"
        witness_time = self.generate_witness(wasm, input_json, wtns)
        
        # Generate proof
        result = self.prove(zkey, wtns, out_dir, circuit_name)
        
        # Update with witness time
        return ProveResult(
            witness=result.witness,
            proof_json=result.proof_json,
            public_json=result.public_json,
            witness_time_s=witness_time,
            prove_time_s=result.prove_time_s,
            peak_rss_mb=result.peak_rss_mb,
            proof_size_bytes=result.proof_size_bytes,
            public_size_bytes=result.public_size_bytes
        )

    def get_proof_info(self, proof_json: Path, public_json: Path) -> dict:
        """Extract information from proof files.
        
        Args:
            proof_json: Path to proof JSON file
            public_json: Path to public inputs JSON file
            
        Returns:
            Dictionary with proof information
        """
        info: dict[str, Any] = {}
        
        try:
            if proof_json.exists():
                with open(proof_json, 'r') as f:
                    proof_data = json.load(f)
                
                info["proof_format"] = "groth16"
                info["proof_fields"] = list(proof_data.keys())
                info["proof_size_bytes"] = proof_json.stat().st_size
                
                # Check for expected Groth16 proof structure
                expected_fields = ["pi_a", "pi_b", "pi_c", "protocol", "curve"]
                missing_fields = [f for f in expected_fields if f not in proof_data]
                if missing_fields:
                    info["warning"] = f"Missing expected fields: {missing_fields}"
            
            if public_json.exists():
                with open(public_json, 'r') as f:
                    public_data = json.load(f)
                
                info["public_inputs_count"] = len(public_data) if isinstance(public_data, list) else 0
                info["public_size_bytes"] = public_json.stat().st_size
                info["public_inputs"] = public_data
                
        except (json.JSONDecodeError, IOError) as e:
            info["error"] = f"Failed to read proof files: {e}"
        
        return info

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        if PSUTIL_AVAILABLE:
            try:
                process = psutil.Process()
                return process.memory_info().rss / (1024 * 1024)
            except Exception:
                pass
        return 0.0

    def _run(self, cmd: list[str]) -> None:
        """Run external command with timeout and error handling."""
        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=self.timeout_s,
                check=False,
                shell=self.use_shell
            )
        except subprocess.TimeoutExpired as e:
            raise ProverError(f"Command timed out: {' '.join(cmd)}") from e
        except FileNotFoundError as e:
            tool = cmd[0]
            raise ProverError(f"Tool not found: {tool}. Please install required tools.") from e
        except Exception as e:
            raise ProverError(f"Failed to run command: {' '.join(cmd)}: {e}") from e
        
        if proc.returncode != 0:
            raise ProverError(
                f"Command failed [{proc.returncode}]: {' '.join(cmd)}\n"
                f"Output: {proc.stdout}"
            )

    def verify_tools(self) -> dict:
        """Verify that required tools are available."""
        tools = {
            "snarkjs": self.snarkjs_bin,
            "node": self.node_bin
        }
        
        status = {}
        
        for tool_name, tool_path in tools.items():
            try:
                result = subprocess.run(
                    [tool_path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=self.use_shell
                )
                
                if result.returncode == 0:
                    version_output = result.stdout.strip()
                    
                    # Special handling for snarkjs banner format
                    if tool_name == "snarkjs":
                        import re
                        m = re.search(r"snarkjs@([0-9][\w\.\-+]*)", version_output)
                        if m:
                            version = m.group(0)
                        else:
                            version = version_output.split('\n')[0] if version_output else "detected"
                    else:
                        version = version_output.split('\n')[0]
                    
                    status[tool_name] = {
                        "available": True,
                        "version": version,
                        "path": tool_path
                    }
                else:
                    status[tool_name] = {
                        "available": False,
                        "error": f"Non-zero exit code: {result.stderr}",
                        "path": tool_path
                    }
                    
            except Exception as e:
                status[tool_name] = {
                    "available": False,
                    "error": str(e),
                    "path": tool_path
                }
        
        return status