"""Create descriptive native-pilot figures and timing summaries from audited data.

Requires matplotlib for figures. No price conversion, population extrapolation,
privacy score or complete-lifecycle cost is inferred by this script.
"""
import argparse
import hashlib
import json
import math
import platform
import statistics
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from check import check


def p95(values):
    """Empirical nearest-rank 95th percentile (rank ceil(0.95*n))."""
    return sorted(values)[math.ceil(.95 * len(values)) - 1]


def main(folder):
    p = Path(folder)
    audit = check(p)
    report = json.loads((p / 'report.json').read_text())
    rows = report['summaries']
    out = p / 'analysis'
    out.mkdir(exist_ok=True)
    colors = ['#176B98', '#D28623', '#327B59', '#7B5AA6']
    names = ['zk_B1', 'zk_B2', 'zk_B4', 'signed_control']
    labels = ['ZK: 4 possible issuers', 'ZK: 2 possible issuers', 'ZK: issuer exposed', 'Signed diagnostic']
    high = {r['scenario']: r for r in rows if r['workload'] == 'HIGH' and r['updates'] == 2}
    fig, axes = plt.subplots(1, 4, figsize=(12, 3.7), sharey=True, layout='constrained')
    for ax, name, label, color in zip(axes, names, labels, colors):
        samples = [high[f'{name}_d{d}_HIGH'] for d in [0, 3600, 86400]]
        vals = [r['authorizations'] for r in samples]
        ax.bar(['0', '1 hour', '24 hours'], vals, color=color, width=.65)
        for i, v in enumerate(vals):
            ax.text(i, v + .08, str(v), ha='center', fontsize=10)
        ax.set_title(label, fontsize=10)
        ax.set_ylim(0, 6)
        ax.set_xlabel('Allowed ordinary delay')
        ax.spines[['top', 'right']].set_visible(False)
    axes[0].set_ylabel('Full authorizations / 100 accesses')
    fig.suptitle('Native pilot: 90 days, unrelated revocations at days 31 and 63', fontsize=12)
    fig.savefig(out / 'authorizations.png', dpi=180)
    fig.savefig(out / 'authorizations.svg')
    plt.close(fig)
    # Separate panels prevent shared deployment from being hidden in user savings.
    selected = [high[f'{name}_d0_HIGH'] for name in names]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout='constrained')
    short = ['ZK B=1', 'ZK B=2', 'ZK B=4', 'Signed\ncontrol']
    axes[0].bar(short, [r['holder_gas'] / 1e6 for r in selected], color=colors)
    axes[0].set_title('One observed holder: approval + 100 accesses')
    axes[0].set_ylabel('Million gas')
    bottom = [0.] * 4
    components = [('operator_setup_gas', 'Operator setup', '#176B98'),
                  ('issuer_initial_publication_gas', 'Initial roots', '#D28623'),
                  ('issuer_status_publication_gas', 'Later revocations', '#327B59')]
    for key, label, color in components:
        values = [r[key] / 1e6 for r in selected]
        axes[1].bar(short, values, bottom=bottom, label=label, color=color)
        bottom = [a + b for a, b in zip(bottom, values)]
    axes[1].set_title('Shared infrastructure and issuer publications')
    axes[1].set_ylabel('Million gas')
    axes[1].legend(fontsize=8, loc='upper left')
    for ax in axes:
        ax.spines[['top', 'right']].set_visible(False)
    fig.suptitle('Native pilot at zero ordinary delay — different privacy profiles', fontsize=12)
    fig.savefig(out / 'actor_gas.png', dpi=180)
    fig.savefig(out / 'actor_gas.svg')
    plt.close(fig)
    sessions = []
    for i in range(1, 4):
        session = json.loads((p / 'timing' / f'session_{i}.json').read_text())
        assert session['session'] == i
        assert session['zkey_sha256'] == report['setup']['zkey_sha256']
        assert session['wasm_sha256'] == report['setup']['wasm_sha256']
        measured = [o for o in session['observations'] if not o['warmup']]
        warmups = [o for o in session['observations'] if o['warmup']]
        assert len(measured) == 10 and len(warmups) == 1
        assert all(o['proof_ms'] > 0 and o['verify_ms'] > 0 for o in measured)
        sessions.append(session)
    assert len({s['pid'] for s in sessions}) == 3
    measurements = [o for s in sessions for o in s['observations'] if not o['warmup']]
    timing = {'n': 30, 'sessions': 3, 'observations_per_session': 10, 'excluded_warmups': 3,
              'p95_definition': 'empirical nearest rank, ceil(0.95*n)', 'operations': {}}
    for key in ['proof_ms', 'verify_ms']:
        vals = [o[key] for o in measurements]
        timing['operations'][key] = {'p50': statistics.median(vals), 'p95': p95(vals),
            'min': min(vals), 'max': max(vals), 'session_medians': [
                statistics.median(o[key] for o in s['observations'] if not o['warmup']) for s in sessions],
            'warmups': [next(o[key] for o in s['observations'] if o['warmup']) for s in sessions]}
    result = {'status': 'PASS', 'audit': audit, 'timing': timing,
              'environment': {'python': platform.python_version(), 'matplotlib': matplotlib.__version__},
              'limits': 'One machine, fixed synthetic input and one setup; no independence across devices or populations. Figures are native descriptive results, not whole-lifecycle euros or an equal-privacy external comparison.'}
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    # A separate manifest covers timing and derived files without modifying the
    # replay's original report or evidence manifest.
    files = [q for q in out.iterdir() if q.name != 'manifest.json'] + list((p / 'timing').glob('session_*.json'))
    files += [Path(__file__)]
    manifest = {str(q.relative_to(p)) if q.is_relative_to(p) else 'source:analyze.py':
                hashlib.sha256(q.read_bytes()).hexdigest() for q in sorted(files)}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folder')
    main(parser.parse_args().folder)
