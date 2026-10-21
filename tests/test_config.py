"""Exercise the real loader, including the category format in shipped YAML."""
from pathlib import Path

import pytest

from benchmark.runner import BenchmarkError, load_config_from_yaml
from run_benchmark import _load_yaml_configs


@pytest.mark.parametrize("name,count", [("benchmark.yaml", 2), ("benchmark-ci.yaml", 1)])
def test_shipped_config_loads_existing_circuits(name, count):
    path = Path("config") / name
    configs = load_config_from_yaml(path)
    cli_configs = _load_yaml_configs(path)
    assert len(configs) == count
    assert [c.circuit_name for c in cli_configs] == [c.circuit_name for c in configs]
    assert all(c.circuit_path.is_file() and c.iterations > 0 for c in configs)


def test_flat_config_remains_supported(tmp_path):
    path = tmp_path / "flat.yaml"
    path.write_text("circuits:\n  - file: basic/multiply.circom\n")
    assert load_config_from_yaml(path)[0].circuit_name == "multiply"


@pytest.mark.parametrize("content", ["circuits: {}", "circuits: [42]", "circuits: {basic: 42}"])
def test_malformed_config_fails_explicitly(tmp_path, content):
    path = tmp_path / "invalid.yaml"
    path.write_text(content)
    with pytest.raises(BenchmarkError):
        load_config_from_yaml(path)
