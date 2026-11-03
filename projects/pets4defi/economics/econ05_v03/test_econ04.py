#!/usr/bin/env python3
"""Automated controls for bounded ECON-04; not a substitute for human review."""
import csv
import tempfile
import unittest
from dataclasses import replace
from decimal import Decimal as D
from pathlib import Path
from economic_model import Config, accounting, produce, rows, select_workload

BASE = Path(__file__).resolve().parent
CONFIG = Config.load(BASE/'run_config.json')
INPUT = BASE/'inputs'

class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res, cls.meta = produce(CONFIG, INPUT)
        cls.by_key={(int(x['deposits_per_user']), x['regime']):x for x in cls.res}

    def test_exact_selected_100_gas(self):
        self.assertEqual(D(self.by_key[100,'B0']['transaction_gas_per_user']),D('8227440'))
        self.assertEqual(D(self.by_key[100,'B1']['transaction_gas_per_user']),D('10661616.6'))
        self.assertEqual(D(self.by_key[100,'B0']['unchecked_gas_per_user']),D('5556651'))
        self.assertEqual(D(self.by_key[100,'B1']['full_authorizations_per_user']),13)
        self.assertEqual(D(self.by_key[100,'B1']['cache_hits_per_user']),87)
        self.assertEqual(D(self.by_key[100,'B0']['full_authorizations_per_user']),3)

    def test_selected_10_methods(self):
        self.assertEqual(self.by_key[10,'B0']['technical_variant'],'signed_direct')
        self.assertEqual(self.by_key[10,'B1']['technical_variant'],'zk_direct')
        self.assertEqual(D(self.by_key[10,'B0']['transaction_gas_per_user']),D('912781'))
        self.assertEqual(D(self.by_key[10,'B1']['transaction_gas_per_user']),D('3420945.2'))

    def test_source_reconciliation_gas_event_counts(self):
        # Every selected workload validates individual event gas totals inside produce().
        self.assertEqual(len(self.res),6)

    def test_allocation_endpoints_and_conservation(self):
        A=D('1.443892019');base=D('1.569624315')
        for alpha in [D(0),D('0.25'),D('0.5'),D('0.75'),D(1)]:
            r=accounting(A,base,alpha,1000)
            self.assertEqual(D(r['user_network_cost_after_cash_equivalent_reimbursement_eur'])+D(r['service_known_network_cost_eur']),base+A)
            self.assertEqual(D(r['service_conditional_reimbursement_eur']),(1-alpha)*A)
        self.assertEqual(D(accounting(A,base,D(1),1000)['service_known_network_cost_eur']),0)
        self.assertEqual(D(accounting(A,base,D(0),1000)['user_network_cost_after_cash_equivalent_reimbursement_eur']),base)

    def test_b2_does_not_change_total_external_gas(self):
        b1=self.by_key[100,'B1'];b2=self.by_key[100,'B2']
        self.assertEqual(b1['transaction_gas_per_user'],b2['transaction_gas_per_user'])
        self.assertEqual(b1['external_total_network_cost_eur'],b2['external_total_network_cost_eur'])
        self.assertEqual(D(b2['service_conditional_reimbursement_eur'])*2,D(b2['allocation_pool_A_eur']))

    def test_alpha_fee_offset_invariance(self):
        A=D('1.443892019'); delta=D('0.12'); f=D('0.21'); s=D('0.49'); m=D('0.13')
        alpha=D('0.5');alpha2=alpha+delta/A;f2=f-delta
        self.assertTrue(D(0)<=alpha2<=D(1))
        user_base=alpha*A+f
        user_new=alpha2*A+f2
        profit_base=f+m-s-(1-alpha)*A
        profit_new=f2+m-s-(1-alpha2)*A
        self.assertEqual(user_base,user_new)
        self.assertEqual(profit_base,profit_new)

    def test_n0_undefined_not_reported(self):
        with self.assertRaisesRegex(ValueError,'N=0'):
            accounting(D(1),D(1),D('0.5'),0)
        with self.assertRaisesRegex(ValueError,'N must be >0'):
            Config.load(self._config_file(population_n=0))

    def _config_file(self,**changes):
        import json
        p=self._temp.name if hasattr(self,'_temp') else None
        if p: return Path(p)
        f=tempfile.NamedTemporaryFile('w',delete=False,suffix='.json')
        self.addCleanup(lambda:Path(f.name).unlink(missing_ok=True))
        x=json.loads((BASE/'run_config.json').read_text())
        x.update(changes)
        f.write(json.dumps(x));f.close();return Path(f.name)

    def test_zero_access_unsupported_not_silent(self):
        with self.assertRaisesRegex(ValueError,'zero-activity'):
            Config.load(self._config_file(activity_examples=[0]))

    def test_negative_pool_and_invalid_share(self):
        with self.assertRaisesRegex(ValueError,'Negative'):
            accounting(D(-1),D(1),D('0.5'),1000)
        with self.assertRaisesRegex(ValueError,'alpha'):
            accounting(D(1),D(1),D('1.1'),1000)

    def test_no_renewals_in_90day_trace(self):
        for row in self.res:
            self.assertEqual(row['credential_renewals_per_user'],'0')
            self.assertIn('unknown',row['unknown_extra_user_cost_eur'])
            self.assertIn('unknown',row['unknown_extra_service_cost_eur'])

    def test_units_and_wei_conversion(self):
        self.assertEqual(D('130658648')/D(10)**9,D('0.130658648'))
        p50= D('0.130658648');rate=D('2164.73');dgas=D('2434176.6')
        diff=dgas*p50*rate/D(10)**9
        a=D(self.by_key[100,'B1']['allocation_pool_A_eur'])-D(self.by_key[100,'B0']['allocation_pool_A_eur'])
        self.assertEqual(a,diff)

    def test_provenance_saved_for_every_input(self):
        self.assertEqual(len(self.meta['input_file_sha256']),3)
        self.assertEqual(self.meta['source_commits_supplied_by_technical_owner']['implementation_snapshot_commit'],
                         '9e5cde998cf15a2fda24d54a2bfad288b107642f')

if __name__ == '__main__':
    unittest.main(verbosity=2)
