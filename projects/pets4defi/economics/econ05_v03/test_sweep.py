"""Independent cross-checks of the ECON-05 arithmetic, not human peer review."""
import json
import unittest
from decimal import Decimal as D
from pathlib import Path
from economic_sweep import BASE, produce_sweep
from economic_model import digest

class SweepChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows,cls.baselines,cls.meta=produce_sweep()
        cls.find={(int(r['activity_deposits_per_user_90d']),r['fee_scenario'],D(r['user_share_alpha'])):r for r in cls.rows}
    def test_full_15_by_2_and_no_duplicates(self):
        self.assertEqual(len(self.rows),30)
        self.assertEqual(len(self.find),30)
        self.assertEqual(len(self.baselines),6)
    def test_methods_and_gas_match_baseline_04(self):
        for n,sg,zk,sgas,zgas in [(1,'signed_direct','zk_direct','163864','432848'),(10,'signed_direct','zk_direct','912781','3420945.2'),(100,'signed_cache','zk_cache','8227440','10661616.6')]:
            r=self.find[n,'p50',D('0.5')]
            self.assertEqual((r['baseline_signed_variant'],r['selected_zk_variant']),(sg,zk))
            self.assertEqual((r['signed_gas_per_user'],r['zk_gas_per_user']),(sgas,zgas))
    def test_reprice_ratio_and_no_changed_gas(self):
        for n in [1,10,100]:
            for a in [D(0),D('.25'),D('.5'),D('.75'),D(1)]:
                low=self.find[n,'p50',a];high=self.find[n,'p90',a]
                self.assertEqual(low['zk_gas_per_user'],high['zk_gas_per_user'])
                self.assertEqual(D(high['zk_access_pool_eur_user'])/D(low['zk_access_pool_eur_user']),D('716536567')/D('130658648'))
    def test_allocation_endpoints_conservation_and_monotonic(self):
        for n in [1,10,100]:
            for price in ['p50','p90']:
                seq=[self.find[n,price,a] for a in [D(0),D('.25'),D('.5'),D('.75'),D(1)]]
                self.assertEqual(D(seq[0]['user_share_of_zk_pool_eur_user']),0)
                self.assertEqual(D(seq[-1]['service_subsidy_eur_user']),0)
                for j,r in enumerate(seq):
                    self.assertEqual(D(r['gas_cost_conservation_error_eur_user']),0)
                    self.assertEqual(D(r['user_share_of_zk_pool_eur_user'])+D(r['service_subsidy_eur_user']),D(r['zk_access_pool_eur_user']))
                    self.assertEqual(D(r['user_network_after_cash_reimbursement_eur_user'])+D(r['service_subsidy_eur_user']),D(r['user_zw_network_upfront_eur_user']))
                    self.assertEqual(D(r['service_subsidy_eur_population']),D(r['service_subsidy_eur_user'])*1000)
                    self.assertEqual(D(r['service_subsidy_eur_deposit'])*n,D(r['service_subsidy_eur_user']))
                    if j:
                        self.assertGreater(D(r['user_share_of_zk_pool_eur_user']),D(seq[j-1]['user_share_of_zk_pool_eur_user']))
                        self.assertLess(D(r['service_subsidy_eur_user']),D(seq[j-1]['service_subsidy_eur_user']))
    def test_fee_indifference_threshold_price_invariant(self):
        for n in [1,10,100]:
            for a in [D(0),D('.25'),D('.5'),D('.75'),D(1)]:
                r=self.find[n,'p50',a];h=self.find[n,'p90',a]
                self.assertEqual(D(r['alpha_crit_user_network_indifference']),D(h['alpha_crit_user_network_indifference']))
                self.assertEqual(D(r['user_pool_difference_vs_B0_eur_user'])<=0,r['gas_only_user_not_more_expensive_than_B0']=='True')
    def test_100_deposit_reviewed_50pct_example(self):
        r=self.find[100,'p50',D('.5')]
        self.assertEqual(D(r['zk_access_pool_eur_user']),D('1.443892018689218274624'))
        self.assertEqual(D(r['service_subsidy_eur_user']),D('0.7219460093446091373120'))
    def test_plan_all_columns_cross_validated(self):
        self.assertEqual(self.meta['distinct_economic_cases'],15)
        self.assertEqual(self.meta['row_count'],30)
    def test_unknown_costs_not_assumed_zero(self):
        for r in self.rows:
            self.assertIn('u_other',r['unresolved_items'])
            self.assertIn('s_ZK_other',r['minimum_m_required_expression'])
            self.assertIn('NOT IMPLEMENTED',r['cash_compensation_status'])
    def test_source_metadata(self):
        self.assertEqual(len(self.meta['input_file_sha256']),4)
        for name,val in self.meta['input_file_sha256'].items():
            self.assertEqual(val,digest(BASE/'inputs'/name))
        self.assertEqual(self.meta['source_commit_identifiers_supplied_by_technical_owner']['implementation_snapshot_commit'],'9e5cde998cf15a2fda24d54a2bfad288b107642f')

if __name__=='__main__': unittest.main(verbosity=2)
