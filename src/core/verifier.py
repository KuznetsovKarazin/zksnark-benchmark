"""
Verifier module for zkSNARK Benchmark Framework.

Handles proof verification with timing measurements and detailed result tracking.
Supports both successful and failed verification cases for benchmarking.
"""

from __future__ import annotations

import json
import platform
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class VerifyResult:
    """Result of proof verification."""
    is_valid: bool
    verify_time_s: float
    error_message: Optional[str] = None


class VerifierError(RuntimeError):
    """Proof verification error."""
    pass


class Verifier:
    """Proof verification with timing and error tracking."""
    
    def __init__(
        self, 
        snarkjs_bin: str = "snarkjs", 
        timeout_s: int = 120
    ):
        """Initialize verifier with tool path.
        
        Args:
            snarkjs_bin: Path to snarkjs binary
            timeout_s: Timeout for verification commands
        """
        self.snarkjs_bin = snarkjs_bin
        self.timeout_s = timeout_s
        self.use_shell = platform.system() == "Windows"

    def verify(
        self, 
        vkey_json: Path, 
        public_json: Path, 
        proof_json: Path
    ) -> VerifyResult:
        """Verify Groth16 proof against verification key and public inputs.
        
        Args:
            vkey_json: Path to verification key JSON file
            public_json: Path to public inputs JSON file  
            proof_json: Path to proof JSON file
            
        Returns:
            VerifyResult with validation status and timing
            
        Raises:
            VerifierError: If verification process fails (not proof invalid)
        """
        # Check input files exist
        for file_path, name in [(vkey_json, "verification key"), 
                               (public_json, "public inputs"), 
                               (proof_json, "proof")]:
            if not file_path.exists():
                raise VerifierError(f"{name} file not found: {file_path}")
        
        # Validate file contents before verification
        self._validate_input_files(vkey_json, public_json, proof_json)
        
        cmd = [
            self.snarkjs_bin, "groth16", "verify",
            str(vkey_json), str(public_json), str(proof_json)
        ]
        
        t0 = time.perf_counter()
        
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
            verify_time = time.perf_counter() - t0
            return VerifyResult(
                is_valid=False,
                verify_time_s=verify_time,
                error_message=f"Verification timed out after {self.timeout_s}s"
            )
        except Exception as e:
            raise VerifierError(f"Failed to run verification: {e}")
        
        verify_time = time.perf_counter() - t0
        
        # Parse verification result
        output = proc.stdout.strip()
        
        if proc.returncode == 0:
            # Successful verification - check output for validity
            is_valid = self._parse_verification_output(output)
            return VerifyResult(
                is_valid=is_valid,
                verify_time_s=verify_time,
                error_message=None if is_valid else f"Proof invalid: {output}"
            )
        else:
            # Verification process failed
            return VerifyResult(
                is_valid=False,
                verify_time_s=verify_time,
                error_message=f"Verification failed [{proc.returncode}]: {output}"
            )

    def batch_verify(
        self,
        verifications: list[tuple[Path, Path, Path]]
    ) -> list[VerifyResult]:
        """Verify multiple proofs and return results.
        
        Args:
            verifications: List of (vkey, public, proof) tuples
            
        Returns:
            List of VerifyResult objects
        """
        results = []
        
        for vkey_json, public_json, proof_json in verifications:
            try:
                result = self.verify(vkey_json, public_json, proof_json)
                results.append(result)
            except VerifierError as e:
                results.append(VerifyResult(
                    is_valid=False,
                    verify_time_s=0.0,
                    error_message=str(e)
                ))
        
        return results

    def verify_with_inputs(
        self,
        vkey_json: Path,
        proof_json: Path,
        public_inputs: list
    ) -> VerifyResult:
        """Verify proof with public inputs provided as list.
        
        Args:
            vkey_json: Path to verification key JSON file
            proof_json: Path to proof JSON file
            public_inputs: List of public input values
            
        Returns:
            VerifyResult with validation status and timing
        """
        import tempfile
        
        # Create temporary public inputs file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            json.dump(public_inputs, tmp, indent=2)
            tmp_public = Path(tmp.name)
        
        try:
            return self.verify(vkey_json, tmp_public, proof_json)
        finally:
            tmp_public.unlink(missing_ok=True)

    def _validate_input_files(
        self, 
        vkey_json: Path, 
        public_json: Path, 
        proof_json: Path
    ) -> None:
        """Validate input files have correct JSON structure."""
        
        # Validate verification key
        try:
            with open(vkey_json, 'r') as f:
                vkey_data = json.load(f)
            
            if not isinstance(vkey_data, dict):
                raise VerifierError("Verification key must be JSON object")
            
            required_vkey_fields = ["protocol", "curve", "nPublic"]
            for field in required_vkey_fields:
                if field not in vkey_data:
                    raise VerifierError(f"Missing field in verification key: {field}")
                    
            if vkey_data.get("protocol") != "groth16":
                raise VerifierError(f"Unsupported protocol: {vkey_data.get('protocol')}")
                
        except json.JSONDecodeError as e:
            raise VerifierError(f"Invalid verification key JSON: {e}")
        except IOError as e:
            raise VerifierError(f"Cannot read verification key: {e}")
        
        # Validate public inputs
        try:
            with open(public_json, 'r') as f:
                public_data = json.load(f)
            
            if not isinstance(public_data, list):
                raise VerifierError("Public inputs must be JSON array")
                
        except json.JSONDecodeError as e:
            raise VerifierError(f"Invalid public inputs JSON: {e}")
        except IOError as e:
            raise VerifierError(f"Cannot read public inputs: {e}")
        
        # Validate proof
        try:
            with open(proof_json, 'r') as f:
                proof_data = json.load(f)
            
            if not isinstance(proof_data, dict):
                raise VerifierError("Proof must be JSON object")
            
            required_proof_fields = ["pi_a", "pi_b", "pi_c", "protocol", "curve"]
            for field in required_proof_fields:
                if field not in proof_data:
                    raise VerifierError(f"Missing field in proof: {field}")
                    
        except json.JSONDecodeError as e:
            raise VerifierError(f"Invalid proof JSON: {e}")
        except IOError as e:
            raise VerifierError(f"Cannot read proof: {e}")

    def _parse_verification_output(self, output: str) -> bool:
        """Parse snarkjs verification output to determine validity.
        
        Args:
            output: Raw stdout from snarkjs verify command
            
        Returns:
            True if proof is valid, False otherwise
        """
        output_lower = output.lower()
        
        # Check for common validity indicators
        if "verification ok" in output_lower or "ok!" in output_lower:
            return True
            
        # Check for invalidity indicators
        if "invalid" in output_lower or "failed" in output_lower or "error" in output_lower:
            return False
        
        # Default: if no clear indicator and no error code, assume valid
        # This handles cases where snarkjs just returns silently on success
        return True

    def get_verification_info(
        self, 
        vkey_json: Path, 
        public_json: Path, 
        proof_json: Path
    ) -> dict:
        """Get detailed information about verification inputs.
        
        Args:
            vkey_json: Path to verification key JSON file
            public_json: Path to public inputs JSON file
            proof_json: Path to proof JSON file
            
        Returns:
            Dictionary with verification metadata
        """
        info = {}
        
        try:
            # Verification key info
            if vkey_json.exists():
                with open(vkey_json, 'r') as f:
                    vkey_data = json.load(f)
                
                info["vkey"] = {
                    "protocol": vkey_data.get("protocol"),
                    "curve": vkey_data.get("curve"), 
                    "nPublic": vkey_data.get("nPublic"),
                    "file_size": vkey_json.stat().st_size
                }
            
            # Public inputs info
            if public_json.exists():
                with open(public_json, 'r') as f:
                    public_data = json.load(f)
                
                info["public_inputs"] = {
                    "count": len(public_data) if isinstance(public_data, list) else 0,
                    "values": public_data,
                    "file_size": public_json.stat().st_size
                }
            
            # Proof info
            if proof_json.exists():
                with open(proof_json, 'r') as f:
                    proof_data = json.load(f)
                
                info["proof"] = {
                    "protocol": proof_data.get("protocol"),
                    "curve": proof_data.get("curve"),
                    "has_pi_a": "pi_a" in proof_data,
                    "has_pi_b": "pi_b" in proof_data,
                    "has_pi_c": "pi_c" in proof_data,
                    "file_size": proof_json.stat().st_size
                }
            
        except Exception as e:
            info["error"] = f"Failed to read verification files: {e}"
        
        return info

    def verify_tools(self) -> dict:
        """Verify that snarkjs is available and working."""
        try:
            result = subprocess.run(
                [self.snarkjs_bin, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                shell=self.use_shell
            )
            
            if result.returncode == 0:
                version = result.stdout.strip().split('\n')[0]
                return {
                    "snarkjs": {
                        "available": True,
                        "version": version,
                        "path": self.snarkjs_bin
                    }
                }
            else:
                return {
                    "snarkjs": {
                        "available": False,
                        "error": f"Non-zero exit code: {result.stderr}",
                        "path": self.snarkjs_bin
                    }
                }
                
        except Exception as e:
            return {
                "snarkjs": {
                    "available": False,
                    "error": str(e),
                    "path": self.snarkjs_bin
                }
            }