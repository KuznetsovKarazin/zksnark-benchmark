#!/usr/bin/env python3
"""Export a small, source-checked economic input set for project participants."""
import argparse
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path

EXPERIMENT = Path(__file__).resolve().parents[1]
REPOSITORY = EXPERIMENT.parents[1]
D = Decimal


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    if not rows:
        raise ValueError(f'No rows for {path.name}')
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, default=EXPERIMENT / 'results')
    parser.add_argument('--out', type=Path, default=REPOSITORY / 'projects/pets4defi/data')
    parser.add_argument('--assumed-eur-per-eth', type=Decimal, default=D('2170'))
    args = parser.parse_args()
    if not args.assumed_eur_per_eth.is_finite() or args.assumed_eur_per_eth <= 0:
        raise ValueError('The assumed exchange rate must be finite and positive')
    source = args.results
    measurements_hash = sha(source / 'measurements.json')
    events = read_csv(source / 'event_measurements.csv')
    architecture = read_csv(source / 'architecture_results.csv')
    for row in events + architecture:
        if row['measurements_sha256'] != measurements_hash:
            raise ValueError('A derived table does not match the measurement file')
    fees = json.loads((source / 'fee_snapshot.json').read_text())
    ethereum = next(n for n in fees['networks'] if n['network'] == 'ethereum')
    if ethereum['status'] != 'available':
        raise ValueError('No verified Ethereum fee observation is available')
    if sha(source / fees['raw_archive']['path']) != fees['raw_archive']['sha256']:
        raise ValueError('Fee archive checksum does not match the summary')
    fee = ethereum['summary']['within_block_effective_p50_block_weighted']
    selected = [r for r in architecture if r['chain'] == 'l1'
                and r['n_accesses'] == '100' and r['population'] == '1000'
                and r['root_churn'] in ('none', 'weekly', 'daily')]
    if len(selected) != 48 or len({r['context_id'] for r in selected}) != 12:
        raise ValueError('Expected 12 workload contexts and four treatments')
    for row in selected:
        if row['horizon_days'] != '90' or row['auth_ttl_days'] != '30':
            raise ValueError('Unexpected horizon or authorization TTL')
        if int(row['full_authorizations_per_user']) + int(row['cache_hits_per_user']) != 100:
            raise ValueError('Access counts do not reconcile')
        components = sum(D(row[k]) for k in (
            'user_action_gas_per_user', 'demo_setup_gas_per_user',
            'registry_update_gas_per_user'))
        if abs(components - D(row['known_execution_gas_per_user'])) > D('0.000001'):
            raise ValueError('Execution-gas components do not reconcile')
    args.out.mkdir(parents=True, exist_ok=True)
    event_fields = ['variant', 'event', 'scope', 'mean', 'median', 'q1', 'q3', 'iqr',
                    'n', 'sample_interpretation']
    event_rows = [{**{k: r[k] for k in event_fields}, 'unit': 'gas',
                   'measurement': 'local_L1_successful_transaction'}
                  for r in events if r['chain'] == 'l1' and r['metric'] == 'gas_used']
    write_csv(args.out / 'event_costs.csv', event_rows)
    workload_fields = ['context_id', 'variant', 'n_accesses', 'apps_deployed',
        'population', 'horizon_days', 'validity_days', 'auth_ttl_days', 'root_churn',
        'credential_issues_per_user', 'credential_refreshes_per_user',
        'root_publications_refresh_population', 'root_publications_background',
        'full_authorizations_per_user', 'cache_hits_per_user',
        'cache_reauthorizations_per_user', 'user_action_gas_per_user',
        'demo_setup_gas_per_user', 'registry_update_gas_per_user',
        'known_execution_gas_per_user']
    workload_rows = [{**{k: r[k] for k in workload_fields},
                      'cache_policy': 'global_invalidation_shared_registry',
                      'renewal_publication_policy': 'unbatched',
                      'cost_boundary': 'known_execution_only',
                      'status': 'projection_from_measured_mean_event_gas'}
                     for r in selected]
    write_csv(args.out / 'workload_costs.csv', workload_rows)
    index = {(r['context_id'], r['variant']): r for r in selected}
    premiums = []
    for context in sorted({r['context_id'] for r in selected}):
        for mode in ('direct', 'cache'):
            signed = index[context, 'signed_' + mode]
            zk = index[context, 'zk_' + mode]
            delta = D(zk['known_execution_gas_per_user']) - D(signed['known_execution_gas_per_user'])
            row = {'context_id': context, 'comparison': 'zk_' + mode + '_minus_signed_' + mode,
                'extra_action_gas_per_user': D(zk['user_action_gas_per_user']) - D(signed['user_action_gas_per_user']),
                'extra_setup_gas_per_user': D(zk['demo_setup_gas_per_user']) - D(signed['demo_setup_gas_per_user']),
                'extra_registry_gas_per_user': D(zk['registry_update_gas_per_user']) - D(signed['registry_update_gas_per_user']),
                'extra_known_execution_gas_per_user': delta,
                'fee_p50_wei_per_gas': fee['p50_wei'], 'fee_p90_wei_per_gas': fee['p90_wei'],
                'assumed_eur_per_eth': args.assumed_eur_per_eth,
                'extra_execution_eur_at_fee_p50': delta * D(fee['p50_wei']) / D(10**18) * args.assumed_eur_per_eth,
                'extra_execution_eur_at_fee_p90': delta * D(fee['p90_wei']) / D(10**18) * args.assumed_eur_per_eth,
                'period_days': '90', 'status': 'fee_scenarios_not_quarterly_cost_quantiles',
                'unknown_differential_costs': 'issuer;witness;user_computation;failures',
                'comparison_boundary': 'matched_global_invalidation_common_registry'}
            premiums.append(row)
    write_csv(args.out / 'privacy_premium.csv', premiums)
    inputs = []

    def add(name, value, unit, status, source_url='', source_date='', evidence_needed='', lower='', upper=''):
        inputs.append({'input': name, 'value': value, 'lower': lower, 'upper': upper,
            'unit': unit, 'status': status, 'source_url': source_url,
            'source_date': source_date, 'evidence_needed': evidence_needed})

    add('ETH_EUR', str(args.assumed_eur_per_eth), 'EUR/ETH', 'assumption_not_market_quote',
        evidence_needed='Use a dated rate if making a monetary claim; this value is only an illustration.')
    add('Ethereum_effective_execution_price', str(D(fee['p50_wei']) / D(10**9)),
        'gwei', 'observed_fee_proxy_p50_with_p10_p90', ethereum['source_url'],
        ethereum['window']['last_block']['timestamp_utc'],
        'Equal-weight distribution of within-block effective p50 prices; exact window in provenance.json.',
        str(D(fee['p10_wei']) / D(10**9)), str(D(fee['p90_wei']) / D(10**9)))
    for family in ('signed', 'zk'):
        for event in ('initial_issuance', 'renewal'):
            add(f'{family}_{event}', '', 'EUR/credential/event', 'missing',
                evidence_needed='Comparable service quote: identity checks, volume, date and whether root-publication gas is included.')
    add('witness_delivery', '', 'EUR/user/update', 'missing',
        evidence_needed='Service scope and volume; separate fetching a path from operating the service; identify invoice overlap.')
    add('proving_service', '', 'EUR/proof', 'missing_optional_service_price',
        evidence_needed='Use only if outsourcing proof generation is part of the scenario; do not also charge the same computation as local work.')
    prover = json.loads((source / 'server_prover.json').read_text())
    warm = prover['summary']['warm_proof_ms']
    add('server_warm_proof_time', str(warm['median']), 'ms/proof',
        'measured_server_median_with_q1_q3', source_date=prover['created_utc'],
        evidence_needed=prover['cpu'] + '; ' + prover['node'] + '; n=30; not phone performance or a price.',
        lower=str(warm['q1']), upper=str(warm['q3']))
    add('phone_proof_time', '', 'ms/proof', 'missing_technical_measurement',
        evidence_needed='Physical device/browser, cold/warm samples and actual circuit; do not substitute server timing.')
    add('user_time_valuation', '', 'EUR/hour', 'missing_optional_valuation',
        evidence_needed='Source and population; elapsed computation does not necessarily occupy the user. No default zero.')
    add('L2_data_and_operator_fee', '', 'ETH/transaction', 'missing_technical_measurement',
        evidence_needed='Serialized transaction and pinned oracle/network state; not available from execution gas alone.')
    add('stale_proof_failures', '', 'events/user/90_days', 'missing_technical_measurement',
        evidence_needed='Separate pre-submission abandonment, included reverts, witness refresh, replacement proof and waiting.')
    add('revocation_delay_Delta', '', 'seconds', 'policy_to_define',
        evidence_needed='Technical lead defines authoritative event and maximum acceptance delay; no legal acceptability assumed.')
    add('revocation_exposure_loss', '', 'EUR/user/90_days', 'missing_optional_risk_model',
        evidence_needed='Use only supported event frequency and consequence estimates; otherwise report exposure time separately.')
    write_csv(args.out / 'input_register.csv', inputs)
    source_names = ['measurements.json', 'event_measurements.csv', 'architecture_results.csv',
                    'fee_snapshot.json', 'fee_history_raw.json.gz', 'ci_provenance.json', 'server_prover.json']
    provenance = {
        'dataset': 'PETs4DeFi eligibility-access economic inputs',
        'measurement_source_sha': selected[0]['source_sha'],
        'source_files': {name: sha(source / name) for name in source_names},
        'source_directory': str(source.relative_to(REPOSITORY)) if source.is_relative_to(REPOSITORY) else str(source),
        'exporter_sha256': sha(Path(__file__)),
        'files': {p.name: sha(p) for p in sorted(args.out.glob('*.csv'))},
        'counts': {'workload_contexts': 12, 'workload_rows': len(selected), 'matched_premiums': len(premiums)},
        'fee_window': ethereum['window'], 'fee_metric': fees['methodology']['summary_metric'],
        'fx': {'assumed_eur_per_eth': str(args.assumed_eur_per_eth), 'status': 'assumption_not_market_quote'},
        'boundary': 'L1 known execution under global cache invalidation; no total cost or ungated baseline',
        'unmeasured': ['independent_signed_status', 'addition_only_invalidation',
            'bounded_revocation_delay', 'batched_population_run', 'ungated_deposit',
            'stale_proof_failures', 'phone_prover', 'complete_L2_fee']}
    (args.out / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print(json.dumps(provenance['counts']))


if __name__ == '__main__':
    main()
