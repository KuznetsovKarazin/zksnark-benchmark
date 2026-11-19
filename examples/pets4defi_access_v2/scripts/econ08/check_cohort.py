"""Reconcile saved cohort transactions with the fixed schedule and actor totals."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
from proof_binding import check_proof_binding


DAY = 86_400
HORIZON = 90 * DAY
TTL = 30 * DAY
AMOUNT = 100 * 10**18


def audit(folder, source_root=None):
    manifest = json.loads((folder / 'manifest.json').read_text())
    assert set(manifest) == {'report.json', 'accesses.json', 'receipts_and_proofs.json.gz', 'verification_key.json'}
    for name, sha256 in manifest.items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == sha256, name
    report = json.loads((folder / 'report.json').read_text())
    if source_root:
        for name, sha256 in report['source_files_sha256'].items():
            assert hashlib.sha256((source_root / name).read_bytes()).hexdigest() == sha256, name
    assert report['status'] == 'PASS' and report['stage'] == 'balanced_cohort'
    design, scenario, context = (report[key] for key in ('design', 'scenario', 'context'))
    assert design['population'] in (16, 128, 512)
    assert design['per_issuer'] * 4 == design['population'] == context['population']
    assert design['observed_holders'] == 4 and design['measured_credential_index'] == 0
    assert design['root_presentation_grace_seconds'] == 0 and design['ttl_seconds'] == TTL
    assert design['horizon_seconds'] == HORIZON and design['registry_capacity_per_issuer'] == 1024
    assert scenario['delta'] in (0, 3600, DAY)
    groups, zk = scenario['groups'], scenario['family'] == 'zk'
    assert (scenario['family'], groups) in {('signed', 1), ('zk', 1), ('zk', 2), ('zk', 4)}
    expected_updates = [(day * DAY, n % 4, 1 + n // 4) for n, day in enumerate(range(7, 85, 7))]
    if scenario['id'].endswith('_control'):
        expected_updates = []
    assert [(u['at'], u['issuer'], u['credential']) for u in scenario['updates']] == expected_updates
    expected_times = [0] if scenario['workload'] == 'LOW' else [i * HORIZON // 100 for i in range(100)]
    assert scenario['workload'] in ('LOW', 'HIGH') and design['access_offsets_seconds'] == expected_times
    assert [h['issuer'] for h in context['holders']] == list(range(4))
    assert len({h['address'] for h in context['holders']}) == 4
    assert all(h['group'] == h['issuer'] * groups // 4 for h in context['holders'])

    accesses = json.loads((folder / 'accesses.json').read_text())
    raw = json.loads(gzip.decompress((folder / 'receipts_and_proofs.json.gz').read_bytes()))
    binding = check_proof_binding(raw)
    txs, proofs = raw['transactions'], raw['proofs']
    gas = Counter()
    by_hash = {}
    for tx in txs:
        receipt, sent = tx['receipt'], tx['transaction']
        assert tx['scenario'] == scenario['id'] and receipt['status'] == 1
        assert sent['hash'] == receipt['hash'] and receipt['hash'] not in by_hash
        assert tx['calldata_bytes'] == (len(sent['data']) - 2) // 2
        by_hash[receipt['hash']] = tx
        category = tx['category']
        if tx.get('excluded_from_system_cost'):
            cost = 'excluded_fixture'
        elif category in {'approval', 'access'}:
            cost = tx['actor']
        elif category in {'deployment', 'partition_setup'}:
            cost = 'operator_setup'
        else:
            assert category in {'initial_publication', 'status_publication'}
            cost = category
        gas[cost] += int(receipt['gasUsed'])
    base = context['base']
    publications = [tx for tx in txs if tx['category'] == 'status_publication']
    assert [(tx['timestamp'] - base, tx['issuer'], tx['credential']) for tx in publications] == expected_updates
    assert Counter(tx['issuer'] for tx in txs if tx['category'] == 'initial_publication') == Counter(range(4))
    components = Counter(tx['component'] for tx in txs if tx['category'] == 'deployment')
    assert components == {'Poseidon': 1, 'PolicyRegistry': groups, 'MockToken': 1, 'PolicyGate': groups,
                          **({'Groth16Verifier': 1} if zk else {})}
    assert Counter(tx['actor'] for tx in txs if tx['category'] == 'approval') == Counter(f'holder_{i}' for i in range(4))
    workload_txs = [tx for tx in txs if tx['category'] in {'access', 'status_publication'}]
    assert len(accesses) == 4 * len(expected_times) == sum(tx['category'] == 'access' for tx in workload_txs)
    assert [(tx['timestamp'], tx['category'] == 'access') for tx in workload_txs] == sorted(
        (tx['timestamp'], tx['category'] == 'access') for tx in workload_txs)
    assert len({row['tx_hash'] for row in accesses}) == len(accesses)
    proof_links = []
    for holder, observed in zip(context['holders'], report['holders'], strict=True):
        issuer, group, address = (holder[key] for key in ('issuer', 'group', 'address'))
        rows = [row for row in accesses if row['holder_issuer'] == issuer]
        assert [row['at'] for row in rows] == expected_times
        previous = None
        full = 0
        for i, row in enumerate(rows):
            at = row['at']
            invalidation = min((t for t, other, _ in expected_updates
                                if previous is not None and previous < t <= at and other * groups // 4 == group), default=None)
            if previous is None:
                event = 'first'
            elif at >= min(previous + TTL, HORIZON) or (zk and invalidation is not None and at >= invalidation + scenario['delta']):
                event = 'reauthorize'
            else:
                event = 'hit'
            assert row['event'] == event and row['group'] == group and row['index'] == i
            before, after = row['before'], row['after']
            assert int(before['nonce']) == i and int(after['nonce']) == i + 1
            assert int(after['deposit']) - int(before['deposit']) == AMOUNT
            assert int(before['holderBalance']) - int(after['holderBalance']) == AMOUNT
            assert int(after['gateBalance']) - int(before['gateBalance']) == AMOUNT
            tx = by_hash[row['tx_hash']]
            assert tx['category'] == 'access' and tx['event'] == event and tx['timestamp'] == base + at
            assert tx['actor'] == f'holder_{issuer}' and tx['receipt']['from'] == address
            assert tx['receipt']['to'] == context['gates'][group] and int(tx['receipt']['gasUsed']) == row['gas']
            link = row['proof_index']
            assert tx['proof_index'] == link and (link is not None) == (zk and event != 'hit')
            if link is not None:
                pr = proofs[link]
                assert pr['index'] == link and pr['scenario'] == scenario['id']
                assert int(pr['nonce']) == i and int(pr['t']) == base + at
                proof_links.append(link)
            if event == 'hit':
                assert before['cache'] == after['cache']
            else:
                assert int(after['cache'][0]) == base + min(at + TTL, HORIZON)
                previous = at
                full += 1
        assert observed == {'issuer': issuer, 'accesses': len(rows), 'authorizations': full, 'gas': gas[f'holder_{issuer}']}
    assert sorted(proof_links) == list(range(len(proofs)))
    for key, value in report['gas'].items():
        expected = sum(gas[f'holder_{i}'] for i in range(4)) if key == 'holder_cohort' else gas[key]
        assert value == expected, key
    return {'scenario': scenario['id'], 'accesses': len(accesses), 'proofs': len(proofs), 'status': 'PASS', **binding}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folders', nargs='+', type=Path)
    parser.add_argument('--source-root', type=Path)
    options = parser.parse_args()
    for folder in options.folders:
        print(json.dumps(audit(folder, options.source_root)))
