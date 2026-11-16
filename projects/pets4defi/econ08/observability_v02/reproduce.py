#!/usr/bin/env python3
"""Offline numerical reproduction; never replace bundled results."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent


def main():
    checks=(ROOT/'SHA256SUMS').read_text().splitlines()
    for line in checks:
        expected,name=line.split('  ',1)
        path=ROOT/name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise SystemExit('Checksum mismatch: '+name)
    print('Package SHA256 checks PASS:',len(checks),flush=True)
    env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
    subprocess.run([sys.executable,'-m','unittest','discover','-s','src','-v'],cwd=ROOT,env=env,check=True)
    with tempfile.TemporaryDirectory(prefix='econ08_observability_') as tmp:
        out=Path(tmp)/'results'
        subprocess.run([sys.executable,str(ROOT/'src/run_pilot.py'),'--out',str(out)],cwd=ROOT,env=env,check=True)
        expected={p.name for p in (ROOT/'results').iterdir() if p.is_file()}
        actual={p.name for p in out.iterdir() if p.is_file()}
        if expected!=actual:raise SystemExit('Output inventory differs')
        for name in sorted(expected):
            if (ROOT/'results'/name).read_bytes()!=(out/name).read_bytes():
                raise SystemExit('Numerical result differs: '+name)
        print('Byte-exact numerical reproduction PASS:',len(expected),'files',flush=True)
        handoff=Path(tmp)/'handoff'
        subprocess.run([sys.executable,str(ROOT/'src/build_handoff.py'),'--results',str(out),
                        '--out',str(handoff)],cwd=ROOT,env=env,check=True)
        for name in ['payment_comparison_REFERENCE.csv','price_inputs.csv']:
            if (ROOT/'handoff'/name).read_bytes()!=(handoff/name).read_bytes():
                raise SystemExit('Handoff result differs: '+name)
        print('Byte-exact economic handoff PASS: 2 files',flush=True)
    print('No EVM measurement or novelty validation is implied by PASS.')


if __name__=='__main__':main()
