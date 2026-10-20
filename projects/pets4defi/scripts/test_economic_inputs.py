import csv
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest

from build_economic_inputs import PROJECT, build, build_tables, load_inputs, policy_model


class EconomicInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = load_inputs()
        cls.tables = build_tables(*cls.inputs)

    def test_three_workloads_not_fifteen_independent_measurements(self):
        workloads = self.tables['frequency_workload_costs.csv']
        self.assertEqual(len(workloads), 15)
        self.assertEqual({r['accesses'] for r in workloads}, {1, 10, 100})
        self.assertEqual(len({r['context_id'] for r in workloads}), 3)
        self.assertEqual({r['variant'] for r in workloads}, set(policy_model.VARIANTS))

    def test_successful_actions_and_event_costs_reconcile(self):
        events = self.tables['frequency_event_counts.csv']
        for row in self.tables['frequency_workload_costs.csv']:
            matching = [e for e in events if (e['context_id'], e['variant']) ==
                        (row['context_id'], row['variant'])]
            self.assertEqual(sum(e['event_count_per_user'] for e in matching
                                 if e['event'] != 'approve'), row['accesses'])
            self.assertEqual(sum(e['projected_gas_per_user'] for e in matching),
                             row['user_transaction_gas_per_user'])
            self.assertEqual(row['credential_renewals_per_user'], 0)
            self.assertEqual(row['unrelated_revocation_publications'], 12)

    def test_one_access_contains_no_recurring_access_or_cache_savings(self):
        rows = [r for r in self.tables['frequency_workload_costs.csv'] if r['accesses'] == 1]
        for row in rows:
            self.assertEqual(row['approvals_per_user'], 1)
            self.assertEqual(row['cache_hits_per_user'], 0)
            self.assertEqual(row['reauthorizations_per_user'], 0)
        decision = self.tables['frequency_decisions.csv'][0]
        self.assertEqual(decision['selected_signed_variant'], 'signed_direct')
        self.assertEqual(decision['selected_zk_variant'], 'zk_direct')

    def test_choices_use_same_context_and_preserve_difference(self):
        for decision in self.tables['frequency_decisions.csv']:
            rows = {r['variant']: r for r in self.tables['frequency_workload_costs.csv']
                    if r['context_id'] == decision['context_id']}
            for family in ('signed', 'zk'):
                expected = min(rows[family + '_' + mode]['user_transaction_gas_per_user']
                               for mode in ('direct', 'cache'))
                self.assertEqual(decision[family + '_user_transaction_gas_per_user'], expected)
            self.assertEqual(decision['zk_minus_signed_user_gas'],
                             decision['zk_user_transaction_gas_per_user'] -
                             decision['signed_user_transaction_gas_per_user'])

    def test_100_access_results_match_existing_published_inputs(self):
        with (PROJECT / 'data/workload_costs.csv').open() as stream:
            existing = {(r['context_id'], r['policy'], r['variant']): r for r in csv.DictReader(stream)}
        for row in self.tables['frequency_workload_costs.csv']:
            if row['accesses'] != 100:
                continue
            before = existing[row['context_id'], row['policy'], row['variant']]
            for field in ('user_transaction_gas_per_user', 'full_authorizations_per_user',
                          'cache_hits_per_user', 'gate_deployment_gas_per_user',
                          'zk_ongoing_publication_budget_gas_per_population'):
                self.assertEqual(Decimal(str(row[field])), Decimal(before[field]), field)
        with (PROJECT / 'data/privacy_premium.csv').open() as stream:
            before = next(r for r in csv.DictReader(stream)
                          if r['context_id'] == 'n100-K1-N1000-I4-L90-weekly-batched'
                          and r['policy'] == 'security')
        after = next(r for r in self.tables['frequency_decisions.csv'] if r['accesses'] == 100)
        for field in ('selected_signed_variant', 'selected_zk_variant'):
            self.assertEqual(before[field], after[field])
        for field in ('zk_minus_signed_user_gas', 'privacy_user_eur_fee_p50',
                      'privacy_user_eur_fee_p90'):
            self.assertEqual(Decimal(before[field]), after[field])

    def test_alpha_plan_holds_workload_fixed_and_does_not_impute_prices(self):
        plans = self.tables['economic_sweep_plan.csv']
        self.assertEqual(len(plans), 15)
        self.assertEqual(len({r['scenario_id'] for r in plans}), 15)
        for n in (1, 10, 100):
            group = [r for r in plans if r['accesses'] == n]
            self.assertEqual({r['private_user_share_alpha'] for r in group},
                             {Decimal(x) for x in ('0', '.25', '.5', '.75', '1')})
            self.assertEqual(len({(r['context_id'], r['baseline_signed_variant'],
                                   r['private_zk_variant']) for r in group}), 1)
            for row in group:
                self.assertEqual(row['private_user_share_alpha'] + row['private_service_share'], 1)
                for field in ('common_fee_f_eur_per_user_period',
                              'other_service_margin_eur_per_user_period', 'fixed_service_cost_eur_per_period'):
                    self.assertEqual(row[field], '')
                for q in ('p50', 'p90'):
                    user = row['private_user_pool_component_eur_fee_' + q]
                    service = row['private_service_pool_component_eur_fee_' + q]
                    self.assertEqual(user + service, row['private_access_pool_eur_fee_' + q])
                self.assertEqual(len({r['private_access_pool_gas_per_user'] for r in group}), 1)

    def test_build_is_deterministic_and_manifest_hashes_match(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            a, b = Path(first), Path(second)
            build(a)
            build(b)
            self.assertEqual({p.name: p.read_bytes() for p in a.iterdir()},
                             {p.name: p.read_bytes() for p in b.iterdir()})
            manifest = json.loads((a / 'economic_inputs_manifest.json').read_text())
            for name, checksum in manifest['files'].items():
                self.assertEqual(policy_model.sha(a / name), checksum)


if __name__ == '__main__':
    unittest.main()
