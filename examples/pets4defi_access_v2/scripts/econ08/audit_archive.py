"""Audit the complete, fixed ECON-08 archive without generating measurements."""
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess

from check import check
from check_cohort import audit

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT.parents[1]
PREFIX = ROOT.relative_to(REPO).as_posix()


def sources(folder):
    report = json.loads((folder / 'report.json').read_text())
    commit = report['git_head']
    assert re.fullmatch(r'[0-9a-f]{40}', commit)
    for name, expected in report['source_files_sha256'].items():
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        blob = subprocess.run(['git', 'show', f'{commit}:{PREFIX}/{name}'],
                              cwd=REPO, check=True, capture_output=True).stdout
        assert hashlib.sha256(blob).hexdigest() == expected, (commit, name)


def main():
    pilot = ROOT / 'results/econ08_native_pilot'
    cohort = ROOT / 'results/econ08_cohort'
    sources(pilot)
    result = check(pilot)
    # Timing and generated figures have a separate historical manifest.
    manifest = json.loads((pilot / 'analysis/manifest.json').read_text())
    for name, expected in manifest.items():
        path = ROOT / 'scripts/econ08/analyze.py' if name == 'source:analyze.py' else pilot / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, name
    sessions = sorted((pilot / 'timing').glob('session_*.json'))
    assert [p.name for p in sessions] == [f'session_{i}.json' for i in range(1, 4)]
    timing_proofs = sum(len(json.loads(p.read_text())['observations']) for p in sessions)
    assert timing_proofs == 33
    folders = sorted((cohort / 'runs').iterdir())
    assert len(folders) == 22 and all(p.is_dir() for p in folders)
    csv_rows = list(csv.DictReader((cohort / 'summary.csv').read_text().splitlines()))
    summary = {row['scenario']: row for row in csv_rows}
    assert len(summary) == len(csv_rows) == 22
    audited = []
    for folder in folders:
        sources(folder)
        row = audit(folder)
        report = json.loads((folder / 'report.json').read_text())
        saved = summary.pop(row['scenario'])
        for key in ('accesses', 'proofs'):
            if key in saved:
                assert int(saved[key]) == row[key], (row['scenario'], key)
        for key, value in report['gas'].items():
            assert int(saved[key]) == value, (row['scenario'], key)
        assert int(saved['authorizations']) == sum(h['authorizations'] for h in report['holders'])
        assert int(saved['measured_boundary_gas']) == sum(report['gas'][k] for k in
            ('holder_cohort', 'operator_setup', 'initial_publication', 'status_publication'))
        audited.append(row)
    assert not summary
    assert sum(r['accesses'] for r in audited) == 7216
    assert sum(r['proofs'] for r in audited) == 392
    print(json.dumps({'status': 'PASS', 'pilot': result, 'cohort_scenarios': len(audited),
        'cohort_accesses': 7216, 'cohort_proofs': 392, 'timing_proofs': timing_proofs,
        'expected_crypto_proofs': result['proofs'] + timing_proofs + 392}, indent=2))


if __name__ == '__main__':
    main()
