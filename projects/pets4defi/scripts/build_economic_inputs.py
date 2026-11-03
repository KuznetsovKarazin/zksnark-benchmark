#!/usr/bin/env python3
"""Export a small frequency sweep and an economic experiment plan.

Reuses archived receipt gas and the existing policy accounting model. This is
post-processing, not another cryptographic benchmark or a completed cash-flow
model. Unsupported service prices and economic outcomes remain unfilled.
"""
from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
REPOSITORY = PROJECT.parents[1]
EXPERIMENT = REPOSITORY / 'examples/pets4defi_access_v2'
POLICY_SOURCE = EXPERIMENT / 'scripts/policy_economics.py'
spec = importlib.util.spec_from_file_location('pets4defi_policy_economics', POLICY_SOURCE)
policy_model = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = policy_model
spec.loader.exec_module(policy_model)

FREQUENCIES = (1, 10, 100)
USER_SHARES = tuple(Decimal(x) for x in ('0', '.25', '.5', '.75', '1'))


def load_inputs():
    measurements_path = EXPERIMENT / 'results/policy_measurements.json'
    fee_path = EXPERIMENT / 'results/fee_snapshot.json'
    fx_path = PROJECT / 'data/fx_quote.json'
    payload = json.loads(measurements_path.read_text())
    if payload['metadata'].get('debug_run'):
        raise ValueError('Debug measurements cannot supply participant inputs')
    if payload['metadata'].get('source_dirty') is not False:
        raise ValueError('Participant inputs require recorded clean measurement sources')
    measurements = policy_model.Measurements(payload)
    policy = next(p for p in measurements.policies if p.id == 'security')
    if (policy.mode, policy.delta_seconds) != (1, 0):
        raise ValueError('This sweep requires immediate security-epoch revocation')
    fees = json.loads(fee_path.read_text())
    network = next(n for n in fees['networks'] if n['network'] == 'ethereum')
    if network['status'] != 'available':
        raise ValueError('An archived Ethereum fee scenario is required')
    archive = fee_path.parent / fees['raw_archive']['path']
    if policy_model.sha(archive) != fees['raw_archive']['sha256']:
        raise ValueError('Fee archive integrity failure')
    fx, fx_metadata = policy_model.load_fx(fx_path)
    provenance = {
        'measurement_source_sha': payload['metadata']['source_sha'],
        'measurement_recorded_at': payload['metadata']['recorded_at'],
        'measurements_sha256': policy_model.sha(measurements_path),
        'policy_model_sha256': policy_model.sha(POLICY_SOURCE),
        'builder_sha256': policy_model.sha(Path(__file__)),
        'fee_snapshot_sha256': policy_model.sha(fee_path),
        'fee_archive_sha256': policy_model.sha(archive),
        'fx_quote_sha256': policy_model.sha(fx_path),
        'debug_run': False,
    }
    return (measurements, policy,
            network['summary']['within_block_effective_p50_block_weighted'],
            fx, fx_metadata, provenance)


def build_tables(measurements, policy, fee, fx, fx_metadata, provenance):
    workloads, events = [], []
    for accesses in FREQUENCIES:
        context = policy_model.Context(1, 90, 'weekly', accesses=accesses)
        for variant in policy_model.VARIANTS:
            row, trace = policy_model.evaluate(context, policy, variant, measurements)
            row.update(provenance)
            workloads.append(row)
            counts = Counter(t['event'] for t in trace)
            counts['approve'] = row['approvals_per_user']
            for event, count in sorted(counts.items()):
                events.append({
                    'context_id': context.id, 'policy': policy.id,
                    'variant': variant, 'event': event,
                    'event_count_per_user': count,
                    'mean_receipt_gas_per_event': measurements.gas(policy.id, variant, event),
                    'projected_gas_per_user': count * measurements.gas(policy.id, variant, event),
                    'count_status': 'synthetic_uniform_access_schedule_not_observed_frequency',
                    'gas_status': 'archived_local_measurement_mean', **provenance})
    decisions = policy_model.decisions(workloads, fee, fx)
    frequency_by_context = {r['context_id']: r['accesses'] for r in workloads}
    for row in decisions:
        row.update(accesses=frequency_by_context[row['context_id']], horizon_days=90,
                   fx_status=fx_metadata['status'],
                   fx_source_url=fx_metadata['source_url'],
                   fx_retrieved_at_utc=fx_metadata['retrieved_at_utc'], **provenance)
    decisions.sort(key=lambda row: row['accesses'])
    plan = []
    for choice in decisions:
        unchecked_gas = choice['signed_user_transaction_gas_per_user'] - choice['signed_minus_unchecked_user_gas']
        signed_pool_gas = choice['signed_minus_unchecked_user_gas']
        private_pool_gas = choice['zk_user_transaction_gas_per_user'] - unchecked_gas
        if min(signed_pool_gas, private_pool_gas) < 0:
            raise ValueError('Eligibility-overhead allocation requires a nonnegative declared pool')
        for alpha in USER_SHARES:
            row = {
                'scenario_id': f"n{choice['accesses']}-alpha{policy_model.cell(alpha)}",
                'context_id': choice['context_id'], 'policy': policy.id,
                'accesses': choice['accesses'], 'horizon_days': 90,
                'baseline_signed_variant': choice['selected_signed_variant'],
                'private_zk_variant': choice['selected_zk_variant'],
                'signed_baseline_user_share': 1,
                'private_user_share_alpha': alpha,
                'private_service_share': 1-alpha,
                'economic_regime': 'B1_user_funded' if alpha == 1 else 'B2_service_supported',
                'fee_rule': 'same_fixed_per_user_period_fee_f_for_B0_B1_B2_held_constant_across_alpha',
                'common_fee_f_eur_per_user_period': '',
                'unchecked_gas_per_user_unpooled': unchecked_gas,
                'baseline_access_pool_gas_per_user': signed_pool_gas,
                'private_access_pool_gas_per_user': private_pool_gas,
                'cost_pool': 'A_j=(selected_family_user_transaction_gas-unchecked_user_transaction_gas)*price',
                'cost_pool_status': 'measured_gas_component_only;extend_only_with_named_nonoverlapping_priced_items',
                'private_user_payment_formula': 'u_private+alpha*A_private+f',
                'private_service_variable_balance_before_m_and_F_formula': 'f-(1-alpha)*A_private-s_private',
                'unpooled_user_cost_u': 'common_unchecked_deposit_cost_plus_explicit_unpooled_user_costs',
                'unpooled_service_cost_s': 'explicit_separately_service_paid_costs;unknowns_not_zero',
                'other_service_margin_eur_per_user_period': '',
                'fixed_service_cost_eur_per_period': '',
                'status': 'experiment_plan_not_estimated_service_profit_or_adoption',
                'implementation_scope': 'modeled_reimbursement_of_overhead;not_separate_chain_invoice_or_paymaster',
                **provenance}
            for quantile in ('p50', 'p90'):
                conversion = Decimal(fee[quantile + '_wei']) / Decimal(10**18) * fx
                row['unchecked_eur_fee_' + quantile] = unchecked_gas * conversion
                row['baseline_access_pool_eur_fee_' + quantile] = signed_pool_gas * conversion
                row['private_access_pool_eur_fee_' + quantile] = private_pool_gas * conversion
                row['private_user_pool_component_eur_fee_' + quantile] = alpha * private_pool_gas * conversion
                row['private_service_pool_component_eur_fee_' + quantile] = (1-alpha) * private_pool_gas * conversion
            plan.append(row)
    return {'frequency_workload_costs.csv': workloads,
            'frequency_event_counts.csv': events,
            'frequency_decisions.csv': decisions,
            'economic_sweep_plan.csv': plan}


def build(out: Path):
    inputs = load_inputs()
    tables = build_tables(*inputs)
    out.mkdir(parents=True, exist_ok=True)
    for filename, rows in tables.items():
        policy_model.write_csv(out / filename, rows)
    manifest = {
        'dataset': 'PETs4DeFi frequency inputs and cost-sharing experiment plan',
        **inputs[-1],
        'command': 'python3 projects/pets4defi/scripts/build_economic_inputs.py',
        'counts': {name: len(rows) for name, rows in tables.items()},
        'fixed_context': {'services': 1, 'credential_validity_days': 90,
                          'authorization_ttl_days': 30, 'horizon_days': 90,
                          'population': 1000, 'issuers': 4, 'policy': 'security',
                          'unrelated_revocations': 'every_7_days',
                          'background_additions': 'daily', 'renewal_batching': 'batched'},
        'frequency_grid': list(FREQUENCIES),
        'user_share_grid': [str(value) for value in USER_SHARES],
        'schedule': 'n uniform accesses at 90*i/n days for i=0..n-1; first access at day0',
        'cohort': 'new_user_at_day0;not_a_returning_user_cohort',
        'unit_of_evidence': 'three_synthetic_workloads;alpha_and_prices_are_postprocessing',
        'price_scope': 'archived_public_Ethereum_scenarios_not_grant_testnet_operating_expenses',
        'selection_scope': 'minimum_user_transaction_gas_within_each_family;not_full_system_minimum',
        'economic_scope': 'plan_only;ECON04_completes_event_ledger_and_cash_flows',
        'exclusions': ['unknown_offchain_prices_not_zero', 'no_measured_demand_or_willingness_to_pay',
                       'no_new_crypto_measurements', 'no_actual_paymaster_or_sponsorship_implementation',
                       'no_complete_service_profitability_estimate'],
        'files': {name: policy_model.sha(out / name) for name in tables},
    }
    (out / 'economic_inputs_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=PROJECT / 'data')
    args = parser.parse_args()
    print(json.dumps(build(args.out)['counts']))


if __name__ == '__main__':
    main()
