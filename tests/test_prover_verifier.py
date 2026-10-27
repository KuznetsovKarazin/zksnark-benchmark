"""
Tests for prover and verifier modules.
"""

import json
import pytest
from pathlib import Path
from src.core.compiler import Compiler
from src.core.setup import Setup
from src.core.prover import Prover, ProverError
from src.core.verifier import Verifier, VerifierError
from src.circuits.base import MultiplyCircuit, CircuitRegistry


class TestProver:
    """Test cases for proof generation."""
    
    def test_prover_tool_verification(self):
        """Test that prover can detect available tools."""
        prover = Prover()
        status = prover.verify_tools()
        
        assert "snarkjs" in status
        assert "node" in status
        assert isinstance(status["snarkjs"]["available"], bool)
        assert isinstance(status["node"]["available"], bool)

    def test_prove_with_multiply_circuit(self, tmp_path: Path):
        """Test complete proof generation workflow."""
        # Skip if circuit doesn't exist
        circuit_path = Path("src/circuits/basic/multiply.circom")
        if not circuit_path.exists():
            pytest.skip("multiply.circom not found")
        
        # Compile circuit
        compiler = Compiler()
        compile_result = compiler.compile(circuit_path, tmp_path / "build")
        
        # Setup keys
        setup = Setup()
        ptau = setup.ensure_ptau(tmp_path / "ptau", power=8)
        setup_result = setup.groth16_setup(
            compile_result.r1cs, ptau, 
            tmp_path / "keys" / compile_result.circuit_name
        )
        
        # Generate inputs
        circuit = MultiplyCircuit()
        inputs = circuit.generate_inputs(seed=42)
        input_file = tmp_path / "input.json"
        circuit.write_inputs_json(inputs, input_file)
        
        # Generate proof
        prover = Prover()
        result = prover.prove_with_witness_generation(
            compile_result.wasm, input_file, setup_result.zkey,
            tmp_path / "proof", "test_multiply"
        )
        
        assert result.witness.exists()
        assert result.proof_json.exists()
        assert result.public_json.exists()
        assert result.witness_time_s > 0
        assert result.prove_time_s > 0
        assert result.proof_size_bytes > 0

    def test_proof_info_extraction(self, tmp_path: Path):
        """Test extraction of proof information."""
        # Create mock proof files
        proof_data = {
            "pi_a": ["1", "2", "1"],
            "pi_b": [["3", "4"], ["5", "6"], ["1", "0"]],
            "pi_c": ["7", "8", "1"],
            "protocol": "groth16",
            "curve": "bn128"
        }
        
        public_data = ["123", "456"]
        
        proof_file = tmp_path / "proof.json"
        public_file = tmp_path / "public.json"
        
        with open(proof_file, 'w') as f:
            json.dump(proof_data, f)
        with open(public_file, 'w') as f:
            json.dump(public_data, f)
        
        prover = Prover()
        info = prover.get_proof_info(proof_file, public_file)
        
        assert info["proof_format"] == "groth16"
        assert info["public_inputs_count"] == 2
        assert "proof_size_bytes" in info
        assert "public_size_bytes" in info


class TestVerifier:
    """Test cases for proof verification."""
    
    def test_verifier_tool_verification(self):
        """Test that verifier can detect snarkjs."""
        verifier = Verifier()
        status = verifier.verify_tools()
        
        assert "snarkjs" in status
        assert isinstance(status["snarkjs"]["available"], bool)

    def test_verify_with_multiply_circuit(self, tmp_path: Path):
        """Test complete verification workflow."""
        circuit_path = Path("src/circuits/basic/multiply.circom")
        if not circuit_path.exists():
            pytest.skip("multiply.circom not found")
        
        # Full workflow: compile -> setup -> prove -> verify
        compiler = Compiler()
        compile_result = compiler.compile(circuit_path, tmp_path / "build")
        
        setup = Setup()
        ptau = setup.ensure_ptau(tmp_path / "ptau", power=8)
        setup_result = setup.groth16_setup(
            compile_result.r1cs, ptau,
            tmp_path / "keys" / compile_result.circuit_name
        )
        
        circuit = MultiplyCircuit()
        inputs = circuit.generate_inputs(seed=42)
        input_file = tmp_path / "input.json"
        circuit.write_inputs_json(inputs, input_file)
        
        prover = Prover()
        prove_result = prover.prove_with_witness_generation(
            compile_result.wasm, input_file, setup_result.zkey,
            tmp_path / "proof", "test_multiply"
        )
        
        # Verify proof
        verifier = Verifier()
        verify_result = verifier.verify(
            setup_result.vkey_json,
            prove_result.public_json,
            prove_result.proof_json
        )
        
        assert verify_result.is_valid is True
        assert verify_result.verify_time_s > 0
        assert verify_result.error_message is None

    def test_verification_input_validation(self, tmp_path: Path):
        """Test validation of verification inputs."""
        verifier = Verifier()
        
        # Test with non-existent files
        fake_vkey = tmp_path / "fake_vkey.json"
        fake_public = tmp_path / "fake_public.json"
        fake_proof = tmp_path / "fake_proof.json"
        
        with pytest.raises(VerifierError):
            verifier.verify(fake_vkey, fake_public, fake_proof)

    def test_verification_info_extraction(self, tmp_path: Path):
        """Test extraction of verification information."""
        # Create mock verification files
        vkey_data = {
            "protocol": "groth16",
            "curve": "bn128",
            "nPublic": 1,
            "vk_alpha_1": ["1", "2", "1"],
            "vk_beta_2": [["3", "4"], ["5", "6"], ["1", "0"]],
            "vk_gamma_2": [["7", "8"], ["9", "10"], ["1", "0"]],
            "vk_delta_2": [["11", "12"], ["13", "14"], ["1", "0"]],
            "vk_alphabeta_12": [],
            "IC": [["15", "16", "1"], ["17", "18", "1"]]
        }
        
        public_data = ["123"]
        
        proof_data = {
            "pi_a": ["1", "2", "1"],
            "pi_b": [["3", "4"], ["5", "6"], ["1", "0"]],
            "pi_c": ["7", "8", "1"],
            "protocol": "groth16",
            "curve": "bn128"
        }
        
        vkey_file = tmp_path / "vkey.json"
        public_file = tmp_path / "public.json"
        proof_file = tmp_path / "proof.json"
        
        for file_path, data in [(vkey_file, vkey_data), (public_file, public_data), (proof_file, proof_data)]:
            with open(file_path, 'w') as f:
                json.dump(data, f)
        
        verifier = Verifier()
        info = verifier.get_verification_info(vkey_file, public_file, proof_file)
        
        assert info["vkey"]["protocol"] == "groth16"
        assert info["vkey"]["nPublic"] == 1
        assert info["public_inputs"]["count"] == 1
        assert info["proof"]["protocol"] == "groth16"
        assert info["proof"]["has_pi_a"] is True


class TestCircuitRegistry:
    """Test cases for circuit registry."""
    
    def test_default_circuits_registration(self):
        """Test that default circuits are registered."""
        registry = CircuitRegistry()
        circuits = registry.list_circuits()
        
        assert "multiply" in circuits
        assert len(circuits) > 0

    def test_circuit_input_generation(self):
        """Test circuit input generation."""
        registry = CircuitRegistry()
        multiply_circuit = registry.get_circuit("multiply")
        
        assert multiply_circuit is not None
        
        inputs = multiply_circuit.generate_inputs(seed=42)
        assert "a" in inputs
        assert "b" in inputs
        assert multiply_circuit.validate_inputs(inputs)

    def test_test_suite_generation(self, tmp_path: Path):
        """Test generation of test suite."""
        registry = CircuitRegistry()
        registry.generate_test_suite(tmp_path, seed=42)
        
        # Check that files were created
        input_files = list(tmp_path.glob("*_input.json"))
        info_files = list(tmp_path.glob("*_info.json"))
        
        assert len(input_files) > 0
        assert len(info_files) > 0
        
        # Verify file contents
        for input_file in input_files:
            with open(input_file, 'r') as f:
                data = json.load(f)
                assert isinstance(data, dict)


# Integration test
class TestIntegrationWorkflow:
    """Integration test for complete workflow."""
    
    @pytest.mark.slow
    def test_complete_workflow_with_registry(self, tmp_path: Path):
        """Test complete workflow using circuit registry."""
        circuit_path = Path("src/circuits/basic/multiply.circom")
        if not circuit_path.exists():
            pytest.skip("multiply.circom not found")
        
        # Initialize all components
        compiler = Compiler()
        setup = Setup()
        prover = Prover()
        verifier = Verifier()
        registry = CircuitRegistry()
        
        # Get circuit and generate inputs
        circuit = registry.get_circuit("multiply")
        inputs = circuit.generate_inputs(seed=123)
        input_file = tmp_path / "input.json"
        circuit.write_inputs_json(inputs, input_file)
        
        # Complete workflow
        compile_result = compiler.compile(circuit_path, tmp_path / "build")
        
        ptau = setup.ensure_ptau(tmp_path / "ptau", power=8)
        setup_result = setup.groth16_setup(
            compile_result.r1cs, ptau,
            tmp_path / "keys" / compile_result.circuit_name
        )
        
        prove_result = prover.prove_with_witness_generation(
            compile_result.wasm, input_file, setup_result.zkey,
            tmp_path / "proof", "integration_test"
        )
        
        verify_result = verifier.verify(
            setup_result.vkey_json,
            prove_result.public_json,
            prove_result.proof_json
        )
        
        # Verify everything worked
        assert compile_result.constraints >= 1
        assert setup_result.zkey.exists()
        assert prove_result.proof_json.exists()
        assert verify_result.is_valid is True
        
        # Check timing measurements
        assert prove_result.witness_time_s > 0
        assert prove_result.prove_time_s > 0
        assert verify_result.verify_time_s > 0

    def test_benchmark_runner_jsonl_serialization(self, tmp_path: Path):
        """Test benchmark runner with JSONL save/load."""
        from benchmark.runner import BenchmarkRunner, BenchmarkConfig
        
        circuit_path = Path("src/circuits/basic/multiply.circom")
        if not circuit_path.exists():
            pytest.skip("multiply.circom not found")
        
        # Create runner and config
        runner = BenchmarkRunner(tmp_path / "work")
        config = BenchmarkConfig(
            circuit_name="multiply",
            circuit_path=circuit_path,
            iterations=1,
            ptau_power=8,
            seed=42
        )
        
        # Run benchmark
        result = runner.run_single_benchmark(config, runner.registry.get_circuit("multiply"))
        assert result.success, result.error_message
        
        # Save and load results
        results_file = tmp_path / "test_results.jsonl"
        runner.save_results_jsonl([result], results_file)
        
        assert results_file.exists()
        
        # Load back and verify
        loaded_results = runner.load_results_jsonl(results_file)
        assert len(loaded_results) == 1
        
        loaded = loaded_results[0]
        assert loaded["success"] == result.success
        assert "circuit_path" in str(loaded["config"])  # Path converted to string
        assert loaded["constraints"] == result.constraints