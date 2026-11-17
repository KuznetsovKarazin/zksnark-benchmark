import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from acquire import load_logs,canonical,REVOKED,SUPPLY_AAVE,WITHDRAW_AAVE,SUPPLY_COMET,WITHDRAW_COMET
from traces import decode
from replay import pattern,evaluate
from observers import hmm


def topic_address(n):return '0x'+format(n,'064x')


class TraceTests(unittest.TestCase):
    def test_beneficiary_semantics(self):
        one,two,three=map(topic_address,[1,2,3])
        supply=decode({'topics':[SUPPLY_AAVE,one,two,topic_address(0)],'data':three+format(100,'064x')},'aave_base')
        self.assertEqual(supply['beneficiary'],'0x'+format(2,'040x'))
        self.assertEqual(supply['initiator'],'0x'+format(3,'040x'))
        withdraw=decode({'topics':[WITHDRAW_AAVE,one,two,three],'data':topic_address(100)},'aave_base')
        self.assertEqual(withdraw['beneficiary'],supply['beneficiary'])
        comet=decode({'topics':[SUPPLY_COMET,one,two],'data':topic_address(100)},'compound_base')
        self.assertEqual(comet['beneficiary'],supply['beneficiary'])
        comet=decode({'topics':[WITHDRAW_COMET,one,two],'data':topic_address(100)},'compound_base')
        self.assertEqual(comet['beneficiary'],'0x'+format(1,'040x'))

    def test_same_timestamp_update_is_absorbed_once(self):
        np.testing.assert_array_equal(pattern([0,10,10,20,30],[10],ttl=30),[1,1,0,0,0])

    def test_sparse_access_is_not_one_full_per_period(self):
        self.assertEqual(sum(pattern([0,89*86400],list(range(86400,90*86400,86400)))),2)

    def test_common_counterfactual_stays_at_uniform_prior(self):
        x=evaluate([[0,10,20,30,40,50]],[[10],[20],[30],[40]],holders=10,policy='common')
        self.assertEqual(x['accuracy'],.25);self.assertEqual(x['identified_fraction'],0)
        self.assertIsNone(x['conditional_identification_median_days'])

    def test_incomplete_empty_acquisition_cannot_mean_zero(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'manifest.json').write_text(json.dumps({'complete':False}))
            with self.assertRaisesRegex(ValueError,'Incomplete coverage'):load_logs(folder)

    def test_corrupt_chunk_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);(p/'chunk.gz').write_bytes(gzip.compress(canonical({'logs':[]})))
            (p/'manifest.json').write_text(json.dumps({'complete':True,'first_block':1,'stop_block_exclusive':2,
                'chunks':[{'first':1,'last':1,'path':'chunk.gz','sha256':'wrong'}]}))
            with self.assertRaisesRegex(ValueError,'Corrupt'):load_logs(folder)

    def test_noiseless_hmm_matches_original_v02_filter(self):
        source=Path(__file__).parents[2]/'observability_v02/src/model.py'
        spec=importlib.util.spec_from_file_location('v02',source);v02=importlib.util.module_from_spec(spec);spec.loader.exec_module(v02)
        updates=[{'at':2,'issuer':0},{'at':3,'issuer':1},{'at':5,'issuer':2},{'at':7,'issuer':3}]
        accesses=[0,1,3,4,6,8];u=np.zeros((4,9),dtype=int)
        for item in updates:u[item['issuer'],item['at']]+=1
        for issuer in range(4):
            rows=v02.generate(accesses,updates,issuer,ttl=3)
            old=v02.infer(rows,updates,ttl=3)
            obs=np.full((1,9),-1)
            for row in rows:obs[0,row['at']]=int(row['refresh'])
            got=hmm(obs,u,.6,ttl=3)
            for row in old:np.testing.assert_allclose(got[0,row['at']],row['posterior'],atol=1e-12)


if __name__=='__main__':unittest.main()
