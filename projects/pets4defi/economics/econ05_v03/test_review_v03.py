import csv,hashlib,unittest
from decimal import Decimal as D
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def load(p):
 with p.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
class ReviewV03(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.core=load(ROOT/'results'/'econ05_sweep_30rows.csv')
  cls.t=load(ROOT/'results'/'thresholds_30rows.csv')
  cls.ph=load(ROOT/'results'/'phase_selected_source_verified_6rows.csv')
  cls.source=load(ROOT/'inputs'/'phase_sensitivity.csv')
 def test_core_30_results(self):self.assertEqual(len(self.core),30)
 def test_thresholds_30_results(self):self.assertEqual(len(self.t),30)
 def test_phase_source_30_rows(self):self.assertEqual(len(self.source),30)
 def test_exactly_one_extension(self):self.assertEqual({x['selected_extension'] for x in self.ph},{'fixed-count revocation phase ONLY'})
 def test_phase_output_six_rows(self):self.assertEqual(len(self.ph),6)
 def test_only_K1_and_fixed_count(self):
  for x in self.ph:self.assertEqual((x['services_K'],x['revocations_count'],x['n_deposits_per_user_90d']),('1','2','100'))
 def test_phase_timing_set(self):self.assertEqual({x['phase_days'] for x in self.ph},{'15/45','30/60','37/67'})
 def test_both_archived_prices(self):
  for p in ['15/45','30/60','37/67']:self.assertEqual({x['archived_fee_scenario'] for x in self.ph if x['phase_days']==p},{'p50','p90'})
 def test_source_gas_and_counts_matched(self):
  for r in self.ph:
   e=next(x for x in self.source if x['apps']=='1' and x['security_event_days']==r['event_days'] and x['variant']=='zk_cache')
   self.assertEqual(D(r['ZK_gas_per_user']),D(e['user_transaction_gas_per_user']))
   self.assertEqual(r['ZK_auth_count'],e['full_authorizations_per_user'])
   self.assertEqual(r['ZK_cache_hits'],e['cache_hits_per_user'])
 def test_phase_total_gas_deltas(self):
  self.assertEqual([D(x['ZK_gas_delta_vs_aligned']) for x in self.ph if x['archived_fee_scenario']=='p50'],[D('288129.8'),D('0'),D('288129.8')])
 def test_all_phase_conservation(self):
  for x in self.ph:self.assertLess(abs(D(x['allocation_conservation_error_EUR'])),D('1e-20'))
 def test_source_hash_and_provenance(self):
  h=hashlib.sha256((ROOT/'inputs'/'phase_sensitivity.csv').read_bytes()).hexdigest()
  self.assertEqual(h,'70ab143e0951cd391571ac972b4a5ccf20ac861ab96c9e9d2811ea7cecdfd3b0')
  for x in self.ph:self.assertEqual(x['source_sha256'],h)
 def test_phase_signed_unchanged(self):self.assertEqual({x['signed_gas_per_user'] for x in self.ph},{'8227440'})
 def test_phase_zk_less_than_signed_all(self):
  for x in self.ph:self.assertLess(D(x['ZK_gas_per_user']),D(x['signed_gas_per_user']))
 def test_phase_shift_cash_reimbursement_uplift(self):
  p={x['phase_days']:x for x in self.ph if x['archived_fee_scenario']=='p50'}
  self.assertLess(abs(D(p['15/45']['service_reimbursement_delta_vs_aligned_EUR'])-D('.0407474164533567790960')),D('1e-16'))
  self.assertEqual(p['15/45']['service_reimbursement_delta_vs_aligned_EUR'],p['37/67']['service_reimbursement_delta_vs_aligned_EUR'])
 def test_core_thresholds_match(self):
  for r,t in zip(self.core,self.t):
   self.assertEqual(D(r['service_subsidy_eur_user']),D(t['service_reimbursement_eur_user']))
   self.assertEqual(D(r['user_pool_difference_vs_B0_eur_user']),D(t['gas_only_user_difference_eur']))
 def test_no_core_phase_cross_mixing(self):
  self.assertTrue(all('12-weekly' in x['weekly_vs_phase_scope'] for x in self.ph))
 def test_one_central_reproduction(self):
  r=next(x for x in self.core if x['activity_deposits_per_user_90d']=='100' and x['fee_scenario']=='p50' and x['user_share_alpha']=='0.5')
  self.assertLess(abs(D(r['user_pool_difference_vs_B0_eur_user'])-D('-.0334618078408697592480')),D('1e-13'))
  self.assertLess(abs(D(r['service_subsidy_eur_user'])-D('.7219460093446091373120')),D('1e-13'))
if __name__=='__main__':unittest.main()
