# src/core/compiler.py
from __future__ import annotations

import hashlib, json, os, re, shutil, subprocess, tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Iterable, Set

@dataclass
class CompileResult:
    circuit_name: str
    r1cs: Path
    wasm: Path
    sym: Optional[Path]
    constraints: int
    versions: dict
    build_dir: Path
    reused_cache: bool

class CompilerError(RuntimeError): ...

class Compiler:
    def __init__(
        self,
        circom_bin: str = "circom",
        snarkjs_bin: str = "snarkjs",
        include_paths: Optional[List[str]] = None,
        compile_flags: Optional[List[str]] = None,
        timeout_s: int = 1200,
    ):
        self.circom_bin = shutil.which(circom_bin) or circom_bin
        self.snarkjs_bin = shutil.which(snarkjs_bin) or snarkjs_bin
        self.include_paths_cfg = include_paths or ["src/circuits", "node_modules"]
        self.compile_flags = compile_flags or ["--r1cs", "--wasm", "--sym"]
        self.timeout_s = timeout_s
        self.abs_includes = self._build_include_list(self.include_paths_cfg)

    def compile(self, circom_file: Path, out_root: Path) -> CompileResult:
        circom_file = Path(circom_file).resolve()
        if not circom_file.exists():
            raise CompilerError(f"Circuit file not found: {circom_file}")
        out_root = Path(out_root); out_root.mkdir(parents=True, exist_ok=True)
        name = circom_file.stem
        build_dir = out_root / name; build_dir.mkdir(parents=True, exist_ok=True)

        deps = self._gather_deps(circom_file, self.abs_includes)
        src_hash = self._hash_files([circom_file] + deps) + "|" + " ".join(self.compile_flags) + "|" + " ".join(map(str, self.abs_includes))
        meta_path = build_dir / "meta.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
                if meta.get("src_hash") == src_hash:
                    r1cs, wasm, sym = self._locate_outputs(build_dir, name)
                    if r1cs and wasm:
                        return CompileResult(
                            name, r1cs, wasm, sym,
                            int(meta.get("constraints", -1)),
                            meta.get("versions", {}), build_dir, True
                        )
            except Exception: pass

        cmd = [self.circom_bin, str(circom_file), "-o", str(build_dir), *self.compile_flags]
        for inc in self.abs_includes: cmd += ["-l", str(inc)]
        self._run(cmd, self.timeout_s)

        r1cs, wasm, sym = self._locate_outputs(build_dir, name)
        if not (r1cs and wasm):
            raise CompilerError(f"Compile outputs not found for {name} in {build_dir}")
        constraints = self._read_constraints(r1cs)
        versions = {
            "circom": self._tool_version([self.circom_bin, "--version"]),
            "snarkjs": self._tool_version([self.snarkjs_bin, "--version"]),
            "node": self._tool_version(["node", "--version"]),
        }
        meta = {
            "circuit": name,
            "src": str(circom_file),
            "deps": [str(p) for p in deps],
            "src_hash": src_hash,
            "compile_flags": self.compile_flags,
            "include_paths": [str(p) for p in self.abs_includes],
            "constraints": constraints,
            "versions": versions,
            "timestamp": int(__import__("time").time()),
        }
        meta_path.write_text(json.dumps(meta, indent=2))
        return CompileResult(name, r1cs, wasm, sym, constraints, versions, build_dir, False)

    def get_circuit_info(self, r1cs_path: Path) -> dict:
        info: dict[str, Any] = {"r1cs_path": str(r1cs_path)}
        if not Path(r1cs_path).exists(): info["error"]="R1CS not found"; return info
        try:
            out = self._check_output([self.snarkjs_bin, "r1cs", "info", str(r1cs_path)])
            info["raw_output"] = out
            pats = {
                "constraints": r"Constraints:\s*(\d+)",
                "variables": r"Variables:\s*(\d+)",
                "private_inputs": r"Private Inputs:\s*(\d+)",
                "public_inputs": r"Public Inputs:\s*(\d+)",
                "labels": r"Labels:\s*(\d+)",
            }
            for k,pat in pats.items():
                m=re.search(pat,out,re.I)
                if m: info[k]=int(m.group(1))
        except Exception as e: info["error"]=str(e)
        try:
            st=Path(r1cs_path).stat(); info["file_size"]=st.st_size; info["mtime"]=st.st_mtime
        except Exception: pass
        return info

    def verify_tools(self) -> dict:
        tools = {"circom": self.circom_bin, "snarkjs": self.snarkjs_bin, "node": "node"}
        out={}
        for n,b in tools.items():
            try: out[n]={"available":True,"version":self._tool_version([b,"--version"]),"path":b}
            except Exception as e: out[n]={"available":False,"error":str(e),"path":b}
        return out

    def cleanup_build_artifacts(self, build_dir: Path, keep_r1cs: bool=True) -> None:
        build_dir=Path(build_dir)
        if not build_dir.exists(): return
        pats=["*.tmp","*.log","*.cpp","*.dat"]; 
        if not keep_r1cs: pats+=["*.r1cs","*.sym"]
        for pat in pats:
            for p in build_dir.glob(pat):
                try: p.unlink()
                except Exception: pass

    # internals
    def _build_include_list(self, base: List[str]) -> List[Path]:
        root=Path.cwd(); incs:List[Path]=[]
        for p in base:
            q=(root/p).resolve()
            if q.exists(): incs.append(q)
        vendor=root/"vendor"
        if vendor.exists():
            for d in sorted(vendor.iterdir()):
                cand=d/"circuits"
                if cand.exists(): incs.append(cand.resolve())
        seen:set[str]=set(); uniq:List[Path]=[]
        for include_path in incs:
            s=str(include_path)
            if s not in seen: uniq.append(include_path); seen.add(s)
        return uniq

    def _locate_outputs(self, build_dir: Path, name: str):
        r1cs = build_dir/f"{name}.r1cs"
        wasm = build_dir/f"{name}_js"/f"{name}.wasm"
        if not wasm.exists(): wasm = build_dir/f"{name}.wasm"
        sym  = build_dir/f"{name}.sym"
        return (r1cs if r1cs.exists() else None,
                wasm if wasm.exists() else None,
                sym if sym.exists() else None)

    def _gather_deps(self, src: Path, incs: List[Path]) -> List[Path]:
        vis:Set[Path]=set(); order:List[Path]=[]
        def dfs(fp:Path):
            if fp in vis: return
            vis.add(fp)
            try: txt=fp.read_text()
            except Exception: return
            for m in re.finditer(r'include\s+"([^"]+)"', txt):
                rel=Path(m.group(1))
                resolved=self._resolve_include(rel, fp.parent, incs)
                if resolved and resolved.exists():
                    dfs(resolved); order.append(resolved)
        dfs(src); return order

    def _resolve_include(self, rel: Path, base: Path, incs: List[Path]) -> Optional[Path]:
        p=(base/rel).resolve()
        if p.exists(): return p
        for inc in incs:
            cand=(inc/rel).resolve()
            if cand.exists(): return cand
        return None

    def _hash_files(self, files: Iterable[Path]) -> str:
        h=hashlib.sha256()
        for p in files:
            try: h.update(Path(p).read_bytes())
            except Exception: h.update(str(p).encode())
        return h.hexdigest()

    def _run(self, cmd: List[str], timeout: int) -> None:
        use_shell = os.name=="nt"
        try:
            proc=subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout, check=False, shell=use_shell)
        except subprocess.TimeoutExpired as e:
            raise CompilerError(f"Command timed out: {' '.join(cmd)}") from e
        except FileNotFoundError as e:
            raise CompilerError(f"Tool not found: {cmd[0]}") from e
        except Exception as e:
            raise CompilerError(f"Failed to run: {' '.join(cmd)}: {e}") from e
        if proc.returncode!=0:
            raise CompilerError(f"Command failed [{proc.returncode}]: {' '.join(cmd)}\n--- OUTPUT ---\n{proc.stdout}")

    def _check_output(self, cmd: List[str]) -> str:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT, shell=(os.name=="nt"))

    def _tool_version(self, cmd: List[str]) -> str:
        try:
            out=self._check_output(cmd).strip()
            if "snarkjs" in cmd[0].lower():
                m=re.search(r"(snarkjs@\S+)", out)
                if m: return m.group(1)
            lines=[l for l in out.splitlines() if l.strip()]
            return lines[0] if lines else "unknown"
        except Exception:
            return "unknown"

    def _read_constraints(self, r1cs_path: Path) -> int:
        try:
            with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=True) as tmp:
                self._run([self.snarkjs_bin,"r1cs","export","json",str(r1cs_path),tmp.name], timeout=300)
                tmp.seek(0); data=json.load(tmp)
                for k in ("constraints","nConstraints"):
                    if k in data: return int(data[k])
        except Exception: pass
        try:
            info=self._check_output([self.snarkjs_bin,"r1cs","info",str(r1cs_path)])
            for pat in (r"Number of constraints:\s*(\d+)", r"Constraints:\s*(\d+)", r"constraints:\s*(\d+)"):
                m=re.search(pat, info, re.I)
                if m: return int(m.group(1))
        except Exception: pass
        try:
            sz=Path(r1cs_path).stat().st_size
            return max(1, sz//100)
        except Exception:
            return 1
