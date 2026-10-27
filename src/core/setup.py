# src/core/setup.py
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict


class SetupError(RuntimeError):
    pass


@dataclass
class SetupResult:
    circuit_name: str
    ptau: Path
    zkey: Path
    vkey_json: Path
    reused_cache: bool


class Setup:
    def __init__(self, snarkjs_bin: str = "snarkjs", timeout_s: int = 600, long_timeout_s: int = 3600):
        self.snarkjs_bin = shutil.which(snarkjs_bin) or snarkjs_bin
        self.timeout_s = int(timeout_s)
        self.long_timeout_s = int(long_timeout_s)

    def ensure_ptau(self, ptau_dir: Path, power: int, curve: str = "bn128") -> Path:
        """Return final PTAU if present; otherwise create it."""
        ptau_dir.mkdir(parents=True, exist_ok=True)
        final = ptau_dir / f"powersOfTau28_hez_final_{power}.ptau"
        if final.exists():
            return final

        tmp = ptau_dir / f"pot_{power}.ptau"
        contrib = ptau_dir / f"contrib_{power}.ptau"

        self._run([self.snarkjs_bin, "powersoftau", "new", curve, str(power), str(tmp)], timeout=self.timeout_s)
        self._run(
            [self.snarkjs_bin, "powersoftau", "contribute", str(tmp), str(contrib), "--name=benchmark", "--entropy=fixed_entropy_123"],
            timeout=self.timeout_s,
        )

        env = os.environ.copy()
        env.setdefault("NODE_OPTIONS", "--max-old-space-size=16384")
        self._run(
            [self.snarkjs_bin, "powersoftau", "prepare", "phase2", str(contrib), str(final)],
            timeout=self.long_timeout_s,
            env=env,
        )

        try:
            tmp.unlink(missing_ok=True)
            contrib.unlink(missing_ok=True)
        except Exception:
            pass

        # Optional verify
        self._run([self.snarkjs_bin, "powersoftau", "verify", str(final)], timeout=self.timeout_s)
        return final

    def groth16_setup(self, r1cs: Path, ptau: Path, keys_dir: Path, circuit_name: Optional[str] = None) -> SetupResult:
        if not r1cs.exists():
            raise SetupError(f"R1CS file not found: {r1cs}")
        if not ptau.exists():
            raise SetupError(f"PTAU file not found: {ptau}")

        keys_dir.mkdir(parents=True, exist_ok=True)
        name = circuit_name or r1cs.stem
        zkey = keys_dir / f"{name}.zkey"
        vkey = keys_dir / f"{name}_vkey.json"

        # cache reuse
        try:
            if zkey.exists() and vkey.exists():
                if zkey.stat().st_mtime >= max(r1cs.stat().st_mtime, ptau.stat().st_mtime):
                    return SetupResult(name, ptau, zkey, vkey, reused_cache=True)
        except Exception:
            pass

        # clean old
        zkey.unlink(missing_ok=True)
        vkey.unlink(missing_ok=True)

        self._run([self.snarkjs_bin, "groth16", "setup", str(r1cs), str(ptau), str(zkey)], timeout=self.long_timeout_s)
        self._run([self.snarkjs_bin, "zkey", "export", "verificationkey", str(zkey), str(vkey)], timeout=self.timeout_s)

        if not zkey.exists() or zkey.stat().st_size < 500:
            raise SetupError("zkey file not created or too small")
        if not vkey.exists() or vkey.stat().st_size < 100:
            raise SetupError("verification key not created or too small")

        self._check_vkey(vkey)
        return SetupResult(name, ptau, zkey, vkey, reused_cache=False)

    def get_ptau_info(self, ptau: Path) -> Dict[str, object]:
        if not ptau.exists():
            return {"error": "PTAU file not found"}
        size = ptau.stat().st_size
        info: Dict[str, object] = {
            "exists": True,
            "file_size": size,
            "file_size_mb": round(size / (1024 * 1024), 2),
        }
        return info

    def verify_tools(self) -> Dict[str, object]:
        use_shell = platform.system() == "Windows"
        try:
            out = subprocess.run([self.snarkjs_bin, "--version"], capture_output=True, text=True, timeout=10, shell=use_shell)
            ok = out.returncode == 0 or "snarkjs" in (out.stdout + out.stderr)
            return {"snarkjs": {"available": ok, "version": (out.stdout or out.stderr).strip().splitlines()[0] if ok else "unknown", "path": self.snarkjs_bin}}
        except subprocess.TimeoutExpired:
            return {"snarkjs": {"available": False, "error": "timeout", "path": self.snarkjs_bin}}
        except Exception as e:
            return {"snarkjs": {"available": False, "error": str(e), "path": self.snarkjs_bin}}

    def _check_vkey(self, vkey: Path) -> None:
        try:
            data = json.loads(vkey.read_text())
            for fld in ("protocol", "curve", "nPublic"):
                if fld not in data:
                    raise SetupError(f"Missing field in verification key: {fld}")
            if data.get("protocol") != "groth16":
                raise SetupError(f"Unexpected protocol: {data.get('protocol')}")
        except Exception as e:
            raise SetupError(f"Invalid verification key JSON: {e}")

    def _run(self, cmd: List[str], timeout: Optional[int] = None, env: Optional[Dict[str, str]] = None) -> None:
        use_shell = platform.system() == "Windows"
        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=timeout or self.timeout_s,
                check=False,
                shell=use_shell,
                env=env,
            )
        except subprocess.TimeoutExpired as e:
            raise SetupError(f"Command timed out after {timeout or self.timeout_s}s: {' '.join(cmd)}") from e
        except FileNotFoundError as e:
            raise SetupError(f"Tool not found: {cmd[0]}") from e
        except Exception as e:
            raise SetupError(f"Failed to run command: {' '.join(cmd)}: {e}") from e
        if proc.returncode != 0:
            raise SetupError(f"Command failed [{proc.returncode}]: {' '.join(cmd)}\n--- OUTPUT ---\n{proc.stdout}")
