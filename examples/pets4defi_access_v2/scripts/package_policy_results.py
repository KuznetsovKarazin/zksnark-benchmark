#!/usr/bin/env python3
"""Preserve policy receipts, proofs and accounting tables byte-for-byte."""
import hashlib
import json
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1] / 'results'
files = sorted(set(root.glob('policy_*.csv')) | {
    root / name for name in ('policy_measurements.json', 'policy_tests.json',
                             'policy_transactions.json', 'policy_proofs.json',
                             'policy_accounting_summary.json')
} | set((root / 'policy_artifacts').glob('*')))
measurement = json.loads((root / 'policy_measurements.json').read_text())
if measurement['metadata']['debug_run'] or measurement['metadata']['runs'] != 30:
    raise ValueError('Final archive requires the 30-run measurement set')
archive_path = root / 'policy_evidence.zip'
rows = []
with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for path in files:
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'Expected evidence file: {path.name}')
        data = path.read_bytes()
        name = path.relative_to(root).as_posix()
        info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.create_system = 3
        info.external_attr = 0o100644 << 16
        archive.writestr(info, data, compresslevel=9)
        rows.append({'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
with zipfile.ZipFile(archive_path) as archive:
    if archive.testzip() is not None:
        raise ValueError('Evidence archive CRC check failed')
    for row in rows:
        assert hashlib.sha256(archive.read(row['path'])).hexdigest() == row['sha256']
manifest = {'archive': archive_path.name, 'sha256': hashlib.sha256(archive_path.read_bytes()).hexdigest(),
            'bytes': archive_path.stat().st_size, 'measurement_source_sha': measurement['metadata']['source_sha'],
            'source_dirty': measurement['metadata']['source_dirty'], 'files': rows}
(root / 'policy_evidence_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({k: v for k, v in manifest.items() if k != 'files'}))
