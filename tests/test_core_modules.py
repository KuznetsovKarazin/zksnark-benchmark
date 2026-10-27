"""
Tests for core compiler and setup modules.
"""

import pytest
from pathlib import Path
from src.core.compiler import Compiler, CompilerError
from src.core.setup import Setup, SetupError


class TestCompiler:
    """Test cases for Circom compiler."""
    
    def test_compile_multiply_circuit(self, tmp_path: Path):
        """Test compilation of basic multiply circuit."""
        compiler = Compiler()
        circuit_path = Path("src/circuits/basic/multiply.circom")
        
        # Skip if circuit doesn't exist
        if not circuit_path.exists():
            pytest.skip("multiply.circom not found")
        
        result = compiler.compile(circuit_path, tmp_path)
        
        assert result.circuit_name == "multiply"
        assert result.constraints >= 1
        assert result.r1cs.exists()
        assert result.wasm.exists()
        assert not result.reused_cache
        
    def test_compile_caching(self, tmp_path: Path):
        """Test that compilation caching works correctly."""
        compiler = Compiler()
        circuit_path = Path("src/circuits/basic/multiply.circom")
        
        if not circuit_path.exists():
            pytest.skip("multiply.circom not found")
        
        # First compilation
        result1 = compiler.compile(circuit_path, tmp_path)
        assert not result1.reused_cache
        
        # Second compilation should use cache
        result2 = compiler.compile(circuit_path, tmp_path)
        assert result2.reused_cache
        assert result2.constraints == result1.constraints
        
    def test_compile_nonexistent_file(self, tmp_path: Path):
        """Test compilation of non-existent file raises error."""
        compiler = Compiler()
        nonexistent = Path("nonexistent.circom")
        
        with pytest.raises(CompilerError):
            compiler.compile(nonexistent, tmp_path)
            
    def test_compiler_version_detection(self):
        """Test that compiler can detect tool versions."""
        compiler = Compiler()
        
        # This should not raise an exception
        version = compiler._tool_version(["echo", "test-version"])
        assert version == "test-version"
        
        # Non-existent tool should return "unknown"
        version = compiler._tool_version(["nonexistent-tool-xyz"])
        assert version == "unknown"


class TestSetup:
    """Test cases for Groth16 setup."""
    
    def test_ptau_generation(self, tmp_path: Path):
        """Test PTAU file generation for small power."""
        setup = Setup()
        
        # Use small power for fast test
        ptau = setup.ensure_ptau(tmp_path, power=4)
        
        assert ptau.exists()
        assert ptau.name == "powersOfTau28_hez_final_4.ptau"
        
        # Second call should reuse existing file
        ptau2 = setup.ensure_ptau(tmp_path, power=4)
        assert ptau2 == ptau
        
    def test_groth16_setup_with_multiply_circuit(self, tmp_path: Path):
        """Test full Groth16 setup with multiply circuit."""
        # Compile circuit first
        compiler = Compiler()
        circuit_path = Path("src/circuits/basic/multiply.circom")
        
        if not circuit_path.exists():
            pytest.skip("multiply.circom not found")
        
        compile_result = compiler.compile(circuit_path, tmp_path / "build")
        
        # Setup PTAU and keys
        setup = Setup()
        ptau = setup.ensure_ptau(tmp_path / "ptau", power=8)
        setup_result = setup.groth16_setup(
            compile_result.r1cs, 
            ptau, 
            tmp_path / "keys" / compile_result.circuit_name
        )
        
        assert setup_result.circuit_name == "multiply"
        assert setup_result.zkey.exists()
        assert setup_result.vkey_json.exists()
        assert not setup_result.reused_cache
        
    def test_setup_caching(self, tmp_path: Path):
        """Test that setup caching works correctly."""
        compiler = Compiler()
        circuit_path = Path("src/circuits/basic/multiply.circom")
        
        if not circuit_path.exists():
            pytest.skip("multiply.circom not found")
        
        compile_result = compiler.compile(circuit_path, tmp_path / "build")
        setup = Setup()
        ptau = setup.ensure_ptau(tmp_path / "ptau", power=8)
        
        # First setup
        keys_dir = tmp_path / "keys" / compile_result.circuit_name
        result1 = setup.groth16_setup(compile_result.r1cs, ptau, keys_dir)
        assert not result1.reused_cache
        
        # Second setup should use cache
        result2 = setup.groth16_setup(compile_result.r1cs, ptau, keys_dir)
        assert result2.reused_cache
        
    def test_ptau_info(self, tmp_path: Path):
        """Test PTAU info extraction."""
        setup = Setup()
        ptau = setup.ensure_ptau(tmp_path, power=4)
        
        info = setup.get_ptau_info(ptau)
        assert "exists" in info
        assert info["exists"] is True
        assert "file_size" in info
        assert info["file_size"] > 0
        # New interface returns structured info
        
    def test_setup_with_invalid_r1cs(self, tmp_path: Path):
        """Test setup with invalid R1CS file."""
        setup = Setup()
        
        # Create fake R1CS file
        fake_r1cs = tmp_path / "fake.r1cs"
        fake_r1cs.write_bytes(b"not a real r1cs file")
        
        ptau = setup.ensure_ptau(tmp_path / "ptau", power=4)
        
        with pytest.raises(SetupError):
            setup.groth16_setup(fake_r1cs, ptau, tmp_path / "keys")


# Integration tests
class TestIntegration:
    """Integration tests for compiler + setup workflow."""
    
    @pytest.mark.slow
    def test_full_workflow(self, tmp_path: Path):
        """Test complete compile -> setup -> verify workflow."""
        circuit_path = Path("src/circuits/basic/multiply.circom")
        
        if not circuit_path.exists():
            pytest.skip("multiply.circom not found")
        
        # Step 1: Compile
        compiler = Compiler()
        compile_result = compiler.compile(circuit_path, tmp_path / "build")
        
        # Step 2: Setup
        setup = Setup()
        ptau = setup.ensure_ptau(tmp_path / "ptau", power=8)
        setup_result = setup.groth16_setup(
            compile_result.r1cs,
            ptau,
            tmp_path / "keys" / compile_result.circuit_name
        )
        
        # Step 3: Verify all artifacts exist
        assert compile_result.r1cs.exists()
        assert compile_result.wasm.exists()
        assert setup_result.zkey.exists()
        assert setup_result.vkey_json.exists()
        
        # Step 4: Check that we can read verification key
        import json
        with open(setup_result.vkey_json) as f:
            vkey = json.load(f)
        
        assert "protocol" in vkey
        assert vkey["protocol"] == "groth16"


# Fixtures and utilities
@pytest.fixture
def sample_circuit_content():
    """Sample Circom circuit for testing."""
    return """pragma circom 2.0.0;

template TestCircuit() {
    signal input a;
    signal input b;
    signal output c;
    
    c <== a * b;
}

component main = TestCircuit();
"""


@pytest.fixture
def temp_circuit(tmp_path: Path, sample_circuit_content: str):
    """Create temporary circuit file for testing."""
    circuit_file = tmp_path / "test_circuit.circom"
    circuit_file.write_text(sample_circuit_content)
    return circuit_file


class TestWithTempCircuit:
    """Tests using temporary circuit files."""
    
    def test_compile_temp_circuit(self, temp_circuit: Path, tmp_path: Path):
        """Test compilation of temporary circuit."""
        compiler = Compiler()
        result = compiler.compile(temp_circuit, tmp_path / "build")
        
        assert result.circuit_name == "test_circuit"
        assert result.constraints >= 1
        assert result.r1cs.exists()
        assert result.wasm.exists()