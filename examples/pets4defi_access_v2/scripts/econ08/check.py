"""Independent, dependency-free audit of saved ECON-08 evidence.

Does not import the JS event oracle and does not trust summary.csv. Reconstructs
cache decisions from the scenario inputs, checks receipt/state links and totals.
Cryptographic verification is performed separately by verify_proofs.mjs.
"""
import argparse
import csv
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
from proof_binding import check_proof_binding

DAY = 86400
TTL = 30 * DAY
HORIZON = 90 * DAY
AMOUNT = 100 * 10**18


def oracle(s):
    expiry = -1
    authorization = None
    result = []
    for at in s['accesses']:
        invalidation = min((e['at'] for e in s['updates']
            if authorization is not None and authorization < e['at'] <= at
            and e['issuer'] // (4 // s['groups']) == 0), default=None)
        fresh = (s['family'] == 'signed' or invalidation is None
                 or at < invalidation + s['delta'])
        event = ('first' if authorization is None else
                 'hit' if at < expiry and fresh else 'reauthorize')
        if event != 'hit':
            authorization, expiry = at, min(at + TTL, HORIZON)
        result.append((at, event))
    return result


def check(folder, source_root=None, allow_smoke=False):
    p = Path(folder)
    manifest = json.loads((p / 'manifest.json').read_text())
    for name, digest in manifest.items():
        assert Path(name).name == name, name
        assert hashlib.sha256((p / name).read_bytes()).hexdigest() == digest, name
    report = json.loads((p / 'report.json').read_text())
    assert report['status'] == ('SMOKE_PASS' if allow_smoke else 'PASS'), report['status']
    assert report['smoke'] == allow_smoke
    if source_root:
        for name, digest in report['source_files_sha256'].items():
            assert hashlib.sha256((Path(source_root) / name).read_bytes()).hexdigest() == digest, name
    raw = json.loads(gzip.decompress((p / 'receipts_and_proofs.json.gz').read_bytes()))
    binding = check_proof_binding(raw)
    accesses = json.loads((p / 'accesses.json').read_text())
    scenarios = report['design']['scenarios']
    assert len(scenarios) == (2 if allow_smoke else 32)
    assert report['design']['population'] == 8
    assert report['design']['root_presentation_grace_seconds'] == 0
    transactions = raw['transactions']
    # Hash alone is not globally unique: independent chains reuse account nonces.
    tx_by_key = {(t['scenario'], t['receipt']['hash']): t for t in transactions}
    assert len(tx_by_key) == len(transactions)
    for t in transactions:
        r = t['receipt']
        assert r['hash'] == t['transaction']['hash']
        assert int(r['gasUsed']) > 0
        assert r['status'] == (0 if t['category'] == 'rejected' else 1)
        assert t['calldata_bytes'] == (len(t['transaction']['data']) - 2) // 2
        assert int(r['blockNumber']) == int(t['transaction']['blockNumber'])
    summaries = {s['scenario']: s for s in report['summaries']}
    csv_summaries = {s['scenario']: s for s in csv.DictReader((p / 'summary.csv').read_text().splitlines())}
    ledger = list(csv.DictReader((p / 'cost_ledger.csv').read_text().splitlines()))
    assert len(ledger) == len(transactions)
    for row, tx in zip(ledger, transactions):
        assert row['scenario'] == tx['scenario'] and row['tx_hash'] == tx['receipt']['hash']
        assert int(row['gas']) == int(tx['receipt']['gasUsed'])
        assert row['actor'] == tx['actor'] and row['category'] == tx['category']
    proof_links = set()
    for s in scenarios:
        rows = [a for a in accesses if a['scenario'] == s['id']]
        assert [(a['at'], a['event']) for a in rows] == oracle(s), s['id']
        txs = [t for t in transactions if t['scenario'] == s['id']]
        pubs = [t for t in txs if t['category'] == 'status_publication']
        context = next(c for c in report['contexts'] if c['id'] == s['id'])
        assert [(t['timestamp'] - context['base'], t['issuer'], t['credential']) for t in pubs] == [
            (u['at'], u['issuer'], u['credential']) for u in s['updates']], s['id']
        assert sum(t['category'] == 'initial_publication' for t in txs) == 4
        assert sum(t['category'] == 'deployment' and t.get('component') == 'PolicyGate' for t in txs) == s['groups']
        assert sum(t['category'] == 'deployment' and t.get('component') == 'Groth16Verifier' for t in txs) == int(s['family'] == 'zk')
        for i, a in enumerate(rows):
            t = tx_by_key[(s['id'], a['tx_hash'])]
            assert t['category'] == 'access' and t['event'] == a['event']
            assert int(t['receipt']['gasUsed']) == a['gas']
            assert t['timestamp'] == context['base'] + a['at']
            assert t['proof_index'] == a['proof_index']
            assert (a['proof_index'] is not None) == (s['family'] == 'zk' and a['event'] != 'hit')
            assert t['receipt']['from'] == t['transaction']['from'] == context['wallet']
            assert t['receipt']['to'] == t['transaction']['to'] == context['gates'][0]
            b, after = a['before'], a['after']
            assert int(b['nonce']) == i and int(after['nonce']) == i + 1
            assert int(after['deposit']) - int(b['deposit']) == AMOUNT
            assert int(after['holderBalance']) - int(b['holderBalance']) == -AMOUNT
            assert int(after['gateBalance']) - int(b['gateBalance']) == AMOUNT
            if a['event'] == 'hit':
                assert b['cache'] == after['cache']
                assert a['proof_index'] is None
            else:
                assert int(after['cache'][0]) == context['base'] + min(a['at'] + TTL, HORIZON)
            if a['proof_index'] is not None:
                proof_links.add(a['proof_index'])
                pr = raw['proofs'][a['proof_index']]
                assert pr['scenario'] == s['id'] and int(pr['nonce']) == i
                assert int(pr['t']) == t['timestamp']
                assert a['proof_ms'] > 0
        def total(predicate):
            return sum(int(t['receipt']['gasUsed']) for t in txs if predicate(t))
        costs = {
            'holder_gas': total(lambda t: t['category'] in ('access', 'approval')),
            'operator_setup_gas': total(lambda t: t['category'] in ('deployment', 'partition_setup') and not t.get('excluded_from_system_cost')),
            'issuer_initial_publication_gas': total(lambda t: t['category'] == 'initial_publication'),
            'issuer_status_publication_gas': total(lambda t: t['category'] == 'status_publication'),
        }
        costs['measured_boundary_gas'] = sum(costs.values())
        costs['excluded_fixture_gas'] = total(lambda t: t.get('excluded_from_system_cost'))
        summary = summaries[s['id']]
        for key, value in costs.items():
            assert summary[key] == value and int(csv_summaries[s['id']][key]) == value, (s['id'], key)
        assert summary['authorizations'] == sum(a['event'] != 'hit' for a in rows)
        assert summary['hits'] == sum(a['event'] == 'hit' for a in rows)
    if not allow_smoke:
        assert report['counts']['workload_accesses'] == 1616
        checks = report['checks']
        assert all(c['passed'] is True for c in checks)
        cases = [c for c in checks if c['name'] == 'own_revocation_case_complete']
        assert {(c['family'], c['groups'], c['delta']) for c in cases} == {
            (f, b, d) for f, b in [('zk', 1), ('zk', 2), ('zk', 4), ('signed', 1)] for d in [0, 3600, DAY]}
        required = {'wrong_wallet', 'wrong_chain', 'wrong_contract', 'wrong_amount', 'wrong_nonce',
                    'cross_group_proof', 'replay', 'ttl_exact', 'credential_expiry_exact',
                    'stale_root_only', 'low_tier', 'forbidden_jurisdiction', 'expired_credential',
                    'not_yet_valid', 'revoked_leaf_cannot_produce_new_membership_proof'}
        assert required <= {c['name'] for c in checks}
        for c in checks:
            if 'before' in c:
                assert c['before'] == c['after']
                assert tx_by_key[(c['scenario'], c['tx_hash'])]['receipt']['status'] == 0
    counts = Counter(t['category'] for t in transactions)
    return {'status': 'PASS', 'scenarios': len(scenarios), 'workload_accesses': sum(len(s['accesses']) for s in scenarios),
            'transactions': len(transactions), 'proofs': len(raw['proofs']), 'categories': dict(counts), **binding}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('folder')
    ap.add_argument('--source-root')
    ap.add_argument('--allow-smoke', action='store_true')
    args = ap.parse_args()
    print(json.dumps(check(args.folder, args.source_root, args.allow_smoke), indent=2))
