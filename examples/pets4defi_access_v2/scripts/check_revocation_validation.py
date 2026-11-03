#!/usr/bin/env python3
"""Offline checks of saved receipts, traces and historical prover samples.

Python standard library only. No RPC, fresh setup or economic-archive changes.
The runtime's assertions and this independent reconstruction are separate checks.
"""
from pathlib import Path
import collections
import gzip
import hashlib
import json
import statistics
import argparse
import os

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out', type=Path, default=Path(os.environ.get('VALIDATION_OUT', ROOT / 'results/revocation_validation')))
parser.add_argument('--analysis-output', type=Path, help='Write analysis here; default is stdout only, leaving saved evidence unchanged.')
args = parser.parse_args()
OUT = args.out.resolve()
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
report = read(OUT / 'validation_report.json')
assert report['status'] == 'PASS'
for name, digest in read(OUT / 'manifest.json').items():
    assert sha(OUT / name) == digest, name
historical_sources_used = []
for name, digest in report['metadata']['source_files_sha256'].items():
    current = ROOT / name
    if sha(current) != digest:
        # Only mutable harness/package metadata may use the saved v0.9 copy.
        # Contracts, circuit, fixtures and dependency lock must still match.
        assert name in ('scripts/revocation_validation.mjs', 'package.json'), name
        original = ROOT / 'scripts/historical_sources/v0.9' / Path(name).name
        assert original.exists() and sha(original) == digest, name
        historical_sources_used.append(name)
traces = read(OUT / 'traces.json')
raw = json.loads(gzip.decompress((OUT / 'receipts_and_proofs.json.gz').read_bytes()))
receipts = {(r['label'], r['receipt']['hash']): r for r in raw['transactions']}
assert len(receipts) == len(raw['transactions'])
historical = report.get('schema_version', 1) == 1
assert len(traces) == (1034 if historical else 800*report['metadata']['repetitions']+400+300)
assert len(raw['proofs']) == report['counts']['proofs']
assert sum(r['kind'] == 'rejected' for r in raw['transactions']) == report['counts']['negative_control_failures']
assert all(c['passed'] for c in report['checks'])
for r in raw['transactions']:
    assert r['receipt']['status'] == (0 if r['kind'] == 'rejected' else 1)
amount = 100 * 10**18
residuals = []
gas_classes = collections.defaultdict(list)
for row in traces:
    r = receipts[row['label'], row['tx_hash']]
    assert int(r['receipt']['gasUsed']) == row['gas']
    before, after = row['before'], row['after']
    for key, change in [('nonce', 1), ('deposit', amount),
                        ('holderBalance', -amount), ('gateBalance', amount)]:
        assert int(after[key]) - int(before[key]) == change
    if row['event'] == 'hit':
        assert before['cache'] == after['cache']
    if row['variant'] == 'zk' and row['event'] == 'reauthorize':
        data = bytes.fromhex(r['transaction']['data'][2:])
        calldata = sum(4 if b == 0 else 16 for b in data)
        changed = sum(before['cache'][i] != after['cache'][i] for i in (0, 2))
        residuals.append(row['gas'] - calldata - 2800 * changed)
        gas_classes[changed].append(row['gas'])
# Empirical state decomposition; not a claim for arbitrary contracts or slots.
assert residuals and set(residuals) == {342621}
if historical: assert len(residuals) == 27
comparison = []
for summary in report['summaries']:
    variant = 'signed' if summary['variant'] == 'signed_global' else summary['variant']
    rows = [r for r in traces if r['label'] == summary['schedule'] and r['variant'] == variant]
    assert len(rows) == 100
    actual = summary['approval_gas'] + sum(r['gas'] for r in rows)
    assert actual == summary['gas']
    shared = variant == 'zk' or summary['variant'] == 'signed_global'
    # Reconstruct independently in integer seconds from receipt timestamps.
    base = receipts[rows[0]['label'], rows[0]['tx_hash']]['timestamp']
    deadline = None
    authorization_time = None
    updates = [d * 86400 for d in summary['revocations']]
    publications = [r for r in raw['transactions'] if r['label']==summary['schedule'] and r['kind']=='revocation']
    if summary.get('groups'):
        assert [r['timestamp']-base for r in publications] == [e['day']*86400 for e in summary['published_revocations']]
        assert [r['issuer'] for r in publications] == [e['issuer'] for e in summary['published_revocations']]
        observed_updates = [r['timestamp']-base for r in publications if r['group']==0]
    else:
        observed_updates = [r['timestamp']-base for r in publications]
    assert observed_updates == updates
    for i, row in enumerate(rows):
        now = int(row['day_seconds'])
        assert now == i * 77760
        assert receipts[row['label'], row['tx_hash']]['timestamp'] == base + now
        outdated = authorization_time is not None and shared and any(authorization_time < u <= now for u in updates)
        expected = 'first' if deadline is None else 'reauthorize' if now >= deadline or outdated else 'hit'
        assert row['event'] == expected
        if expected != 'hit':
            authorization_time = now
            deadline = min(now + 30*86400, 90*86400)
        assert int(row['after']['cache'][0]) == base + deadline
    assert sum(r['event'] != 'hit' for r in rows) == summary['authorizations']
    if summary['variant'] == 'zk' and not summary.get('groups'):
        k = summary['authorizations']
        projection = 7780318.6 + 288129.8 * (k-3)
        signed = next(s for s in report['summaries'] if s['schedule'] == summary['schedule'] and s['variant'] == 'signed')['gas']
        comparison.append(dict(schedule=summary['schedule'], k=k, actual_gas=actual,
                               projected_gas=round(projection, 1),
                               actual_minus_projection=round(actual-projection, 1),
                               delta_gas=actual-signed))
        assert (actual-signed < 0) == (k <= 4)
# Finite observed-range envelope includes the five new first-use samples and
# all observed reauthorization states, including capped validity and stale epochs.
envelopes = []
for k in (4, 5):
    bounds = {}
    for variant, count in [('signed', 3), ('zk', k)]:
        samples = [s for s in report['stateSamples'] if s['variant'] == variant]
        first = [s['first'] for s in samples] or [r['gas'] for r in traces if r['variant']==variant and r['event']=='first' and not r['label'].startswith('shared_signed')]
        reauth = [r['gas'] for r in traces if r['variant'] == variant and r['event'] == 'reauthorize' and not r['label'].startswith('shared_signed')]
        hits = [s['hit'] for s in samples] or [r['gas'] for r in traces if r['variant']==variant and r['event']=='hit' and not r['label'].startswith('shared_signed')]
        bounds[variant] = [46463+f(first)+(count-1)*f(reauth)+(100-count)*f(hits) for f in (min,max)]
    low, high = bounds['zk'][0]-bounds['signed'][1], bounds['zk'][1]-bounds['signed'][0]
    assert (high < 0) if k == 4 else (low > 0)
    envelopes.append(dict(k=k, min_delta=low, max_delta=high))
prover = read(ROOT / 'results/server_prover.json')
assert prover['circuit_sha256'] == sha(ROOT / 'circuits/access.circom')
assert all(x['verified'] for group in ('cold', 'warm') for x in prover[group])
assert len(prover['cold']) == len(prover['warm']) == 30
prover_summary = {}
for group in ('cold', 'warm'):
    xs = sorted(x['proof_time_ms'] for x in prover[group])
    def quantile(p):
        index = (len(xs)-1)*p; lo = int(index); hi = min(lo+1,len(xs)-1)
        return xs[lo]+(xs[hi]-xs[lo])*(index-lo)
    prover_summary[group] = dict(n=len(xs), median_ms=statistics.median(xs), q1_ms=quantile(.25),q3_ms=quantile(.75))
result = dict(status='PASS', receipt_count=len(receipts), trace_count=len(traces),
              ordered_core_and_control_paths=sum(100 for s in report['summaries']), failed_transactions=report['counts']['negative_control_failures'],
              proof_count=len(raw['proofs']),historical_harness_sources_verified=historical_sources_used,
              state_decomposition=dict(n=len(residuals), residual_gas=342621,
                 formula='gas = 342621 + calldata gas + 2800*(changed until + changed security epoch)',
                 observed_classes={str(k):dict(n=len(v),min=min(v),max=max(v)) for k,v in gas_classes.items()}),
              actual_vs_fixed_means=comparison, observed_range_envelopes=envelopes,
              historical_server_proving=prover_summary,
              historical_prover_source_sha256=sha(ROOT / 'results/server_prover.json'),
              limitations='Finite synthetic states, not confidence intervals. Server timings are historical and are not device costs. No external colleague or cryptographic audit.')
if args.analysis_output:
    args.analysis_output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
