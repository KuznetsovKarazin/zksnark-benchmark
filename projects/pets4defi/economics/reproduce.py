#!/usr/bin/env python3
"""Verify and reproduce the attributed economic core without modifying it."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
manifest = json.loads((ROOT / 'SOURCE_MANIFEST.json').read_text())
for item in manifest['files']:
    path = ROOT / item['path']
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != item['sha256']:
        raise SystemExit(f'Source hash mismatch: {path}')
print(f"Verified {len(manifest['files'])} verbatim source files.", flush=True)

with tempfile.TemporaryDirectory(prefix='pets4defi-economics-') as temp:
    work = Path(temp) / 'econ05_v03'
    shutil.copytree(ROOT / 'econ05_v03', work)
    for script in ['economic_sweep.py', 'derive_review_extensions_v03.py',
                   'independent_central_result.py']:
        subprocess.run([sys.executable, script], cwd=work, check=True)
    subprocess.run([sys.executable, '-m', 'unittest', '-v',
                    'test_econ04.py', 'test_sweep.py', 'test_review_v03.py'],
                   cwd=work, check=True)
    outputs = ['econ05_sweep_30rows.csv', 'b0_reference_6rows.csv',
               'thresholds_30rows.csv', 'phase_selected_source_verified_6rows.csv']
    for name in outputs:
        expected = (ROOT / 'econ05_v03' / 'results' / name).read_bytes()
        actual = (work / 'results' / name).read_bytes()
        if actual != expected:
            raise SystemExit(f'Numeric output differs from archived bytes: {name}')
    print('PASS: 39 economic tests and four byte-identical numeric CSV outputs.')
    print('Archived files unchanged; temporary reproduction removed.')
