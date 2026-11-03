import unittest
import json
import tempfile
from collections import Counter
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from policy_economics import (Context, DAY, Measurements, Policy, access_trace,
    cache_hits, comparisons, decisions, evaluate, exposure_rows, load_fx,
    phase_sensitivity, scenario)


GLOBAL = Policy('global', 0, 0, 0)
SECURITY = Policy('security', 1, 0, 300)
DELAY = Policy('delay_300', 2, 300, 300)


def measurements_fixture():
    unit_costs = {'access_first': 10, 'access_repeat': 5, 'approve': 3,
        'cache_register_first': 50, 'cache_reauthorize': 40, 'cache_hit': 8,
        'cache_hit_grace': 12, 'deploy_gate': 1000, 'issuer_addition': 100,
        'issuer_security_update': 300, 'batch_security_update': 500,
        'public_id_revoke': 200, 'issuer_root_initial': 700}
    return Measurements({'metadata': {'policies': [{'id': 'security', 'mode': 1,
        'delta_seconds': 0, 'root_grace_seconds': 300}]}, 'events': [
        {'policy': 'shared', 'variant': 'shared', 'event': name, 'gas_used': gas,
         'evidence_status': 'measured_local'} for name, gas in unit_costs.items()]})


def trace(policy, variant, times, security=(), publications=None, expiry=100000, ttl=100000):
    return access_trace(list(map(Fraction, times)), [Fraction(expiry)]*len(times),
        apps=1, ttl_seconds=ttl, policy=policy, variant=variant,
        security_times=list(map(Fraction, security)),
        publications=Counter(security) if publications is None else publications)


class CacheTraceTests(unittest.TestCase):
    def test_signed_selective_ignores_unrelated_security_updates(self):
        counts, _ = trace(SECURITY, 'signed_cache', [0, 10, 20, 30], security=[10, 20])
        self.assertEqual(counts['cache_register_first'], 1)
        self.assertEqual(counts['cache_hit'], 3)

    def test_global_control_resets_on_additions(self):
        counts, rows = trace(GLOBAL, 'signed_cache', [0, 10, 20], publications=Counter({10: 1}))
        self.assertEqual(counts['cache_reauthorize'], 1)
        self.assertEqual(rows[1]['reason'], 'publication')

    def test_selective_zk_ignores_additions(self):
        counts, _ = trace(SECURITY, 'zk_cache', [0, 10, 20], publications=Counter({10: 1}))
        self.assertEqual(counts['cache_hit'], 2)

    def test_zero_delay_rejects_at_security_event(self):
        _, rows = trace(SECURITY, 'zk_cache', [0, 99, 100, 101], security=[100])
        self.assertEqual(rows[1]['event'], 'cache_hit')
        self.assertEqual(rows[2]['event'], 'cache_reauthorize')

    def test_exact_delta_boundary(self):
        _, rows = trace(DELAY, 'zk_cache', [0, 100, 399, 400, 401], security=[100])
        self.assertEqual(rows[2]['event'], 'cache_hit_grace')
        self.assertEqual(rows[3]['event'], 'cache_reauthorize')
        self.assertEqual(rows[4]['event'], 'cache_hit')

    def test_later_revocation_does_not_extend_old_cache(self):
        _, rows = trace(DELAY, 'zk_cache', [0, 100, 399, 400], security=[100, 250])
        self.assertEqual(rows[2]['old_security_deadline_seconds'], 400)
        self.assertEqual(rows[3]['event'], 'cache_reauthorize')

    def test_expiry_remains_hard_bound_during_delay(self):
        _, rows = trace(DELAY, 'zk_cache', [0, 100, 149, 150], security=[100], ttl=150)
        self.assertEqual(rows[2]['event'], 'cache_hit_grace')
        self.assertEqual(rows[3]['event'], 'cache_reauthorize')
        self.assertIn('expiry', rows[3]['reason'])

    def test_same_timestamp_security_events_use_first_time(self):
        _, rows = trace(DELAY, 'zk_cache', [0, 100, 399, 400], security=[100, 100, 100])
        self.assertEqual(rows[2]['old_security_deadline_seconds'], 400)
        self.assertEqual(rows[3]['event'], 'cache_reauthorize')

    def test_more_apps_does_not_multiply_total_demand(self):
        c = Context(5, 90, 'weekly')
        times, expiries, _, _, security, publications = scenario(c)
        counts, _ = access_trace(times, expiries, apps=5, ttl_seconds=30*DAY,
            policy=SECURITY, variant='signed_cache', security_times=security, publications=publications)
        self.assertEqual(counts['cache_register_first']+counts['cache_reauthorize']+counts['cache_hit'], 100)
        self.assertEqual(counts['approve'], 5)

    def test_renewals_stop_after_last_access(self):
        c = Context(1, 30, 'none', accesses=1)
        _, _, renewals, _, _, _ = scenario(c)
        self.assertEqual(renewals, [])

    def test_two_renewal_rounds_in_quarter(self):
        c = Context(1, 30, 'none')
        _, _, renewals, _, _, _ = scenario(c)
        self.assertEqual(len(renewals), 2)

    def test_batching_changes_publication_count_not_cohort_renewal_count(self):
        a = scenario(Context(1, 30, 'none', 'batched'))
        b = scenario(Context(1, 30, 'none', 'unbatched'))
        self.assertEqual(a[2], b[2])
        self.assertEqual(sum(b[-1].values())-sum(a[-1].values()), 2*(1000-4))

    def test_renewal_replacements_are_security_events(self):
        _, _, renewals, _, security, _ = scenario(Context(1, 30, 'none'))
        self.assertEqual(Counter(security), Counter({time: 4 for time in renewals}))

    def test_population_and_additions_fit_tree_capacity(self):
        Context(1, 90, 'none').validate()
        with self.assertRaisesRegex(ValueError, 'capacity'):
            Context(1, 90, 'none', issuers=1).validate()

    def test_exposure_is_not_counted_as_successful_user_savings(self):
        rows = exposure_rows([DELAY])
        by_time = {r['offset_from_authoritative_revoke_seconds']: r for r in rows}
        self.assertTrue(by_time[299]['old_authorization_accepted'])
        self.assertFalse(by_time[300]['old_authorization_accepted'])
        self.assertNotIn('gas_saved', by_time[300])
        self.assertFalse(by_time[0]['emergency_accepted_at_or_after_revoke'])

    def test_direct_root_presentation_is_distinct_from_cached_grace(self):
        rows = exposure_rows([Policy('delay_3600', 2, 3600, 300)])
        at_end = next(r for r in rows if r['offset_from_authoritative_revoke_seconds'] == 3599)
        self.assertTrue(at_end['old_authorization_accepted'])
        self.assertEqual(at_end['old_root_zk_direct_presentation_max_seconds'], 300)
        self.assertEqual(at_end['authorization_type'], 'preexisting_signed_or_zk_cache')

    def test_direct_and_ungated_are_same_number_of_actions(self):
        for variant in ('unchecked', 'signed_direct', 'zk_direct'):
            counts, _ = trace(DELAY, variant, [0, 100, 400], security=[100])
            self.assertEqual(counts['access_first'], 1)
            self.assertEqual(counts['access_repeat'], 2)
            self.assertEqual(counts['cache_hit'], 0)

    def test_root_grace_not_used_as_cache_expiry(self):
        counts, _ = trace(SECURITY, 'zk_cache', [0, 100, 1000], publications=Counter({100: 1}))
        self.assertEqual(counts['cache_hit'], 2)

    def test_grace_has_distinct_price_and_does_not_reset_cache(self):
        counts, rows = trace(DELAY, 'zk_cache', [0, 50, 100, 399, 400], security=[100])
        self.assertEqual(counts['cache_hit'], 1)
        self.assertEqual(counts['cache_hit_grace'], 2)
        self.assertEqual(cache_hits(counts), 3)
        self.assertEqual(rows[3]['old_security_deadline_seconds'], 400)
        self.assertEqual(rows[4]['event'], 'cache_reauthorize')
        m = measurements_fixture()
        priced = sum(n*m.gas(DELAY.id, 'zk_cache', event) for event, n in counts.items() if n)
        self.assertEqual(priced, 3 + 50 + 8 + 2*12 + 40)

    def test_phase_sensitivity_holds_event_count_constant(self):
        rows, _ = phase_sensitivity(measurements_fixture())
        self.assertEqual(len(rows), 30)
        zk = {r['security_event_days']: r for r in rows if r['apps'] == 1 and r['variant'] == 'zk_cache'}
        self.assertEqual({r['unrelated_revocation_publications'] for r in zk.values()}, {2})
        self.assertGreater(zk['37;67']['full_authorizations_per_user'], zk['30;60']['full_authorizations_per_user'])
        signed = {r['full_authorizations_per_user'] for r in rows if r['apps'] == 1 and r['variant'] == 'signed_cache'}
        self.assertEqual(signed, {3})


class AccountingTests(unittest.TestCase):
    def test_missing_measured_event_fails_closed(self):
        m = Measurements({'metadata': {'policies': []}, 'events': []})
        with self.assertRaises(ValueError):
            m.gas('security', 'zk_cache', 'cache_hit')

    def test_synthetic_or_reverted_rows_cannot_enter_success_gas(self):
        for status in ('assumed', 'measured_included_revert'):
            with self.assertRaises(ValueError):
                Measurements({'metadata': {'policies': []}, 'events': [{
                    'policy': 'security', 'variant': 'zk_cache', 'event': 'cache_hit',
                    'gas_used': 100, 'evidence_status': status}]})

    def test_compared_costs_have_same_boundary_and_units(self):
        rows = []
        costs = {'unchecked': 10, 'signed_direct': 30, 'signed_cache': 20,
                 'zk_direct': 100, 'zk_cache': 25}
        for variant, gas in costs.items():
            rows.append({'context_id': 'one', 'policy': 'security', 'variant': variant,
                'user_transaction_gas_per_user': Decimal(gas),
                'gate_deployment_gas_per_user': Decimal(1), 'horizon_days': 90,
                'delta_seconds': 0, 'root_grace_seconds': 300})
        result = comparisons(rows, {'p50_wei': '1000000000', 'p90_wei': '2000000000'}, Decimal(2000))
        direct, cached = result
        self.assertEqual(direct['signed_minus_unchecked_user_gas'], 20)
        self.assertEqual(direct['zk_minus_signed_user_gas'], 70)
        self.assertEqual(direct['privacy_user_eur_fee_p50'], Decimal('0.00014'))
        self.assertEqual(cached['zk_minus_signed_user_gas'], 5)

    def test_batch_replacement_uses_batch_measurement_and_separate_cost_boundary(self):
        unit_costs = {'access_first': 10, 'access_repeat': 5, 'approve': 3,
            'deploy_gate': 1000, 'issuer_addition': 100, 'issuer_security_update': 300,
            'batch_security_update': 500, 'public_id_revoke': 200, 'issuer_root_initial': 700}
        payload = {'metadata': {'policies': []}, 'events': [
            {'policy': 'shared', 'variant': 'shared', 'event': name, 'gas_used': gas,
             'evidence_status': 'measured_local'} for name, gas in unit_costs.items()]}
        measurements = Measurements(payload)
        batched, _ = evaluate(Context(1, 30, 'none'), SECURITY, 'unchecked', measurements)
        unbatched, _ = evaluate(Context(1, 30, 'none', 'unbatched'), SECURITY, 'unchecked', measurements)
        self.assertEqual(batched['zk_ongoing_publication_budget_gas_per_population'], 89*100 + 8*500)
        self.assertEqual(unbatched['zk_ongoing_publication_budget_gas_per_population'], 89*100 + 2000*300)
        self.assertEqual(batched['zk_initial_roots_gas_per_population'], 4*700)
        self.assertEqual(batched['signed_public_id_publication_budget_gas_per_population'], 0)
        self.assertEqual(batched['user_transaction_gas_per_user'], 10 + 99*5 + 3)
        self.assertEqual(batched['user_transaction_gas_per_user'], unbatched['user_transaction_gas_per_user'])

    def test_decision_chooses_both_families_by_action_cost_only(self):
        costs = {'unchecked': 10, 'signed_direct': 20, 'signed_cache': 30,
                 'zk_direct': 100, 'zk_cache': 25}
        rows = [{'context_id': 'one', 'policy': 'security', 'variant': variant,
            'user_transaction_gas_per_user': Decimal(gas),
            'gate_deployment_gas_per_user': Decimal(999 if variant == 'signed_direct' else 1),
            'delta_seconds': 0, 'root_grace_seconds': 300} for variant, gas in costs.items()]
        row, = decisions(rows, {'p50_wei': '1000000000', 'p90_wei': '2000000000'}, Decimal(2000))
        self.assertEqual(row['selected_signed_variant'], 'signed_direct')
        self.assertEqual(row['selected_zk_variant'], 'zk_cache')
        self.assertEqual(row['zk_minus_signed_user_gas'], 5)
        self.assertEqual(row['signed_minus_unchecked_user_gas'], 10)
        self.assertEqual(row['selected_signed_gate_deployment_gas_per_user'], 999)
        self.assertIn('not_full_system_minimum', row['boundary'])

    def test_observed_fx_requires_source_and_assumption_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'fx.json'
            quote = {'base': 'ETH', 'quote': 'EUR', 'value': '2164.73',
                     'retrieved_at_utc': '2026-10-20T00:00:00Z',
                     'source_url': 'https://example.invalid/test-fixture', 'status': 'observed_web_quote'}
            path.write_text(json.dumps(quote))
            value, metadata = load_fx(path)
            self.assertEqual(value, Decimal('2164.73'))
            self.assertEqual(metadata['status'], 'observed_web_quote')
            _, assumed = load_fx(path, Decimal(2000))
            self.assertEqual(assumed['status'], 'explicit_cli_assumption_not_market_quote')
            del quote['source_url']
            path.write_text(json.dumps(quote))
            with self.assertRaisesRegex(ValueError, 'source URL'):
                load_fx(path)


if __name__ == '__main__':
    unittest.main()
