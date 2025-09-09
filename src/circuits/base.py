"""
Base circuit classes for zkSNARK Benchmark Framework.

Provides abstract interface for circuit input generation and validation.
Each circuit type implements specific input generation logic.
"""

from __future__ import annotations

import json, subprocess, shutil
import random
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional



class BaseCircuit(ABC):
    """Abstract base class for benchmark circuits."""
    
    def __init__(self, name: str, description: str = ""):
        """Initialize circuit.
        
        Args:
            name: Circuit identifier
            description: Human-readable description
        """
        self.name = name
        self.description = description

    @abstractmethod
    def generate_inputs(self, seed: Optional[int] = None) -> Dict[str, Any]:
        """Generate valid inputs for this circuit.
        
        Args:
            seed: Random seed for reproducible generation
            
        Returns:
            Dictionary mapping signal names to values
        """
        pass

    @abstractmethod
    def get_expected_constraints(self) -> int:
        """Get expected number of constraints for this circuit.
        
        Returns:
            Approximate constraint count
        """
        pass

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate that inputs are correct for this circuit.
        
        Args:
            inputs: Input dictionary to validate
            
        Returns:
            True if inputs are valid
        """
        try:
            # Basic validation - check all required signals present
            required_signals = self._get_required_signals()
            for signal in required_signals:
                if signal not in inputs:
                    return False
            return True
        except Exception:
            return False

    @abstractmethod
    def _get_required_signals(self) -> List[str]:
        """Get list of required input signal names."""
        pass

    def write_inputs_json(self, inputs: Dict[str, Any], output_path: Path) -> None:
        """Write inputs to JSON file for circuit.
        
        Args:
            inputs: Input dictionary  
            output_path: Path to write JSON file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(inputs, f, indent=2, ensure_ascii=False)

    def get_circuit_info(self) -> Dict[str, Any]:
        """Get metadata about this circuit.
        
        Returns:
            Dictionary with circuit information
        """
        return {
            "name": self.name,
            "description": self.description,
            "expected_constraints": self.get_expected_constraints(),
            "required_signals": self._get_required_signals(),
            "circuit_type": self.__class__.__name__
        }


class MultiplyCircuit(BaseCircuit):
    """Simple multiplication circuit: c = a * b."""
    
    def __init__(self):
        super().__init__(
            name="multiply",
            description="Basic multiplication: c = a * b"
        )

    def generate_inputs(self, seed: Optional[int] = None) -> Dict[str, Any]:
        """Generate random multiplication inputs."""
        if seed is not None:
            random.seed(seed)
        
        # Generate inputs in reasonable range to avoid overflow
        a = random.randint(1, 1000)
        b = random.randint(1, 1000)
        
        return {
            "a": str(a),  # Circom expects string representation
            "b": str(b)
        }

    def get_expected_constraints(self) -> int:
        return 1  # Single multiplication constraint

    def _get_required_signals(self) -> List[str]:
        return ["a", "b"]

class QuadraticCircuit(BaseCircuit):
    """Quadratic relation: y = a*x*x + b*x + c (y enforced inside the circuit)."""
    def __init__(self):
        super().__init__(
            name="quadratic",
            description="Quadratic: y = a*x^2 + b*x + c"
        )

    def generate_inputs(self, seed: Optional[int] = None) -> Dict[str, Any]:
        if seed is not None:
            random.seed(seed)
        a = random.randint(1, 50)
        b = random.randint(1, 50)
        c = random.randint(1, 50)
        x = random.randint(1, 50)
        return {"a": str(a), "b": str(b), "c": str(c), "x": str(x)}

    def get_expected_constraints(self) -> int:
        return 8  

    def _get_required_signals(self) -> List[str]:
        return ["a", "b", "c", "x"]


class RangeProofCircuit(BaseCircuit):
    """Range proof circuit: prove value is in range [min, max]."""
    
    def __init__(self, min_val: int = 0, max_val: int = 100, bits: int = 8):
        self.min_val = min_val
        self.max_val = max_val
        self.bits = bits
        
        super().__init__(
            name="range_proof",
            description=f"Range proof: value in [{min_val}, {max_val}] using {bits} bits"
        )

    def generate_inputs(self, seed: Optional[int] = None) -> Dict[str, Any]:
        """Generate value within specified range."""
        if seed is not None:
            random.seed(seed)
        
        value = random.randint(self.min_val, self.max_val)
        
        return {
            "value": str(value),
            "min": str(self.min_val),
            "max": str(self.max_val)
        }

    def get_expected_constraints(self) -> int:
        # Rough estimate: bit decomposition + range checks
        return self.bits * 3

    def _get_required_signals(self) -> List[str]:
        return ["value", "min", "max"]


class HashCircuit(BaseCircuit):
    """Hash circuit for cryptographic primitives."""
    
    def __init__(self, hash_type: str = "poseidon", num_inputs: int = 2):
        self.hash_type = hash_type
        self.num_inputs = num_inputs
        
        super().__init__(
            name=f"{hash_type}_hash",
            description=f"{hash_type.upper()} hash with {num_inputs} inputs"
        )

    def generate_inputs(self, seed: Optional[int] = None) -> Dict[str, Any]:
        """Generate hash function inputs."""
        if seed is not None:
            random.seed(seed)
        
        inputs = {}
        
        # Generate input values (field elements)
        for i in range(self.num_inputs):
            # Use safe range for BN254 field
            value = random.randint(1, 2**200)
            inputs[f"in{i}"] = str(value)
        
        return inputs

    def get_expected_constraints(self) -> int:
        # Rough estimates for different hash functions
        if self.hash_type == "poseidon":
            return self.num_inputs * 150  # Poseidon is efficient
        elif self.hash_type == "sha256":
            return self.num_inputs * 25000  # SHA-256 is constraint-heavy
        else:
            return self.num_inputs * 1000  # Generic estimate

    def _get_required_signals(self) -> List[str]:
        return [f"in{i}" for i in range(self.num_inputs)]

class PoseidonHashCircuit(BaseCircuit):
    """Poseidon hash with t inputs (default: 2)."""
    def __init__(self, t: int = 2):
        self.t = t
        super().__init__(
            name="poseidon_hash",
            description=f"Poseidon hash with {t} inputs"
        )

    def generate_inputs(self, seed: Optional[int] = None) -> Dict[str, Any]:
        if seed is not None:
            random.seed(seed)
        # Field-like values as decimal strings
        arr = [str(random.randint(1, 2**200)) for _ in range(self.t)]
        return {"in": arr}

    def get_expected_constraints(self) -> int:
        # ballpark for Poseidon(2) on BN254
        return 240 if self.t == 2 else 150 * self.t

    def _get_required_signals(self) -> List[str]:
        # Circom: signal input in[t];
        return ["in"]


class MerklePoseidonCircuit(BaseCircuit):
    """Merkle membership proof over Poseidon(2) with a fixed depth."""
    def __init__(self, depth: int = 16, name: Optional[str] = None):
        self.depth = depth
        super().__init__(
            name=name or f"merkle_poseidon_{depth}",
            description=f"Merkle(Poseidon) membership, depth={depth}"
        )

    def generate_inputs(self, seed: Optional[int] = None) -> Dict[str, Any]:
        # Try to use local generator first, fallback to node script
        try:
            from merkle_tree_generator import generate_merkle_inputs
            inputs = generate_merkle_inputs(self.depth, leaf_index=0 if seed is None else (seed % (1 << self.depth)), seed=seed)
            
            # Verify proof locally before returning
            from merkle_tree_generator import verify_proof_locally
            if not verify_proof_locally(inputs):
                raise RuntimeError("Generated proof failed local verification")
            
            return inputs
            
        except ImportError:
            # Fallback to node script if merkle_tree_generator not available
            idx = 0 if seed is None else (seed % (1 << self.depth))
            node = shutil.which("node")
            if not node:
                raise RuntimeError("node is required to generate merkle inputs")
            script = Path("scripts/gen_merkle_poseidon.js")
            if not script.exists():
                raise RuntimeError(f"missing generator script: {script}")
            out = subprocess.check_output(
                [node, str(script), str(self.depth), str(idx)],
                text=True
            )
            data = json.loads(out)
            # Validate keys expected by circuit
            for k in ["leaf", "pathElements", "pathIndex", "root"]:
                assert k in data, f"missing key {k} in generated inputs"
            return data

    def _get_required_signals(self) -> List[str]:
        return ["leaf", "pathElements", "pathIndex", "root"]

    def get_expected_constraints(self) -> int:
        return 2 * self.depth + self.depth * 2 * 60



class ECDSACircuit(BaseCircuit):
    def __init__(self):
        super().__init__(
            name="ecdsa_verify",
            description="ECDSA signature verification (secp256k1)"
        )

    def generate_inputs(self, seed: Optional[int] = None) -> Dict[str, Any]:
        node = shutil.which("node")
        if not node:
            raise RuntimeError("node is required to generate ECDSA inputs")
        script = Path("scripts/gen_ecdsa.js")
        if not script.exists():
            raise RuntimeError(f"missing generator script: {script}")
        out = subprocess.check_output([node, str(script), str(seed or 42)], text=True)
        data = json.loads(out)
        # sanity
        for k in ["msg", "pubKeyX", "pubKeyY", "r", "s"]:
            assert k in data, f"missing key {k}"
            assert isinstance(data[k], list) and len(data[k]) == 32, f"{k} must be 32-byte array"
        return data

    def get_expected_constraints(self) -> int:
        # ballpark for a full secp256k1 verifier (non-native): 1e5..2e5+
        return 150_000

    def _get_required_signals(self) -> List[str]:
        return ["msg", "pubKeyX", "pubKeyY", "r", "s"]
 




class CircuitRegistry:
    """Registry for available benchmark circuits."""
    
    def __init__(self):
        self._circuits = {}
        self._register_default_circuits()

    def register(self, circuit: BaseCircuit) -> None:
        """Register a circuit in the registry."""
        self._circuits[circuit.name] = circuit

    def get_circuit(self, name: str) -> Optional[BaseCircuit]:
        """Get circuit by name."""
        return self._circuits.get(name)

    def list_circuits(self) -> List[str]:
        """Get list of available circuit names."""
        return list(self._circuits.keys())

    def get_all_circuits(self) -> Dict[str, BaseCircuit]:
        """Get all registered circuits."""
        return self._circuits.copy()

    def _register_default_circuits(self) -> None:
        self.register(MultiplyCircuit())                    # "multiply"
        self.register(QuadraticCircuit())                   # "quadratic"
        self.register(PoseidonHashCircuit(t=2))             # "poseidon_hash"
        self.register(MerklePoseidonCircuit(depth=4))       # "merkle_poseidon_4"
        self.register(MerklePoseidonCircuit(depth=16))      # "merkle_poseidon_16"
        self.register(ECDSACircuit())                       # "ecdsa_verify"


    def generate_test_suite(self, output_dir: Path, seed: int = 42) -> None:
        """Generate input files for all circuits."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for name, circuit in self._circuits.items():
            inputs = circuit.generate_inputs(seed)
            input_file = output_dir / f"{name}_input.json"
            circuit.write_inputs_json(inputs, input_file)
            
            # Also write circuit info
            info_file = output_dir / f"{name}_info.json"
            with open(info_file, 'w') as f:
                json.dump(circuit.get_circuit_info(), f, indent=2)