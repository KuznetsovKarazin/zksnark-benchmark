import itertools
import math
import random
import unittest
from model import *


class ModelTests(unittest.TestCase):
    def test_ttl_boundary(self):
        self.assertFalse(needs_refresh(9,0,10,0,[]))
        self.assertTrue(needs_refresh(10,0,10,0,[]))

    def test_delta_boundary(self):
        self.assertFalse(needs_refresh(6,0,100,2,[5]))
        self.assertTrue(needs_refresh(7,0,100,2,[5]))

    def test_publication_before_same_time_authorization(self):
        self.assertFalse(needs_refresh(6,5,100,0,[5]))

    def test_renewal_during_grace_supersedes_old_update(self):
        self.assertFalse(needs_refresh(9,6,100,3,[5]))

    def test_new_update_does_not_postpone_earliest_deadline(self):
        self.assertTrue(needs_refresh(7,0,100,2,[5,6]))

    def test_private_fields_rejected(self):
        with self.assertRaises(ValueError):
            infer([{'at':0,'refresh':True,'issuer':0}],[])

    def test_prior_is_retained_without_information(self):
        prior=[.7,.1,.1,.1]
        obs=generate([0,1,3],[],0,ttl=8)
        self.assertEqual(infer(obs,[],ttl=8,prior=prior)[-1]['posterior'],prior)

    def test_one_targeted_update_posterior(self):
        u=[{'at':2,'issuer':0}]
        p=infer([{'at':0,'refresh':True},{'at':3,'refresh':True}],u,ttl=8,rho=.25)[-1]['posterior']
        self.assertAlmostEqual(p[0],1/(1+3*.25))

    def test_negative_observation_excludes_issuer(self):
        u=[{'at':2,'issuer':0}]
        p=infer([{'at':0,'refresh':True},{'at':3,'refresh':False}],u,ttl=8,rho=.75)[-1]['posterior']
        self.assertEqual(p[0],0)
        self.assertAlmostEqual(p[1],1/3)

    def test_uniform_cover_equals_common(self):
        for seed in range(50):
            rng=random.Random(seed)
            u=[{'at':rng.randrange(1,100),'issuer':rng.randrange(4)} for _ in range(20)]
            a=sorted(rng.sample(range(100),30))
            for delta in [0,3]:
                x=generate(a,u,seed%4,ttl=12,delta=delta,policy='common',seed=seed)
                y=generate(a,u,seed%4,ttl=12,delta=delta,policy='event_cover',rho=1,seed=seed)
                self.assertEqual(x,y)

    def test_every_access_reveals_no_issuer(self):
        u=[{'at':2,'issuer':0}]
        o=generate([0,1,3,5],u,0,policy='every',ttl=8)
        self.assertEqual(infer(o,u,policy='every',ttl=8)[-1]['entropy'],2)

    def test_unknown_label_permutation_control(self):
        u=[{'at':2,'issuer':0}]
        o=generate([0,3,5],u,0,ttl=8)
        self.assertEqual(anonymous_label_posterior(o,u,4,8,0),[.25]*4)

    def test_three_fresh_sets_singleton(self):
        h=availability_trace([[0,1,2],[1,2,3],[0,2,3]],2,4,3,'fresh_k')
        self.assertEqual([x['positive_support'] for x in h],[3,2,1])
        self.assertTrue(all(x['accepted'] for x in h))

    def test_single_visible_rejection_can_identify(self):
        h=availability_trace([[0,1,2]],3,4,3,'fresh_k')
        self.assertEqual(h[0]['support'],1)

    def test_guard_cannot_split_four_with_k_three(self):
        for mask in range(15):
            s={j for j in range(4) if mask>>j&1}
            self.assertEqual(admissible_accept_set(range(4),s,3,'guard_k'),set())

    def test_guard_protects_rejecting_branch(self):
        self.assertEqual(admissible_accept_set(range(4),{0,1,2},2,'guard_k'),{0,1})

    def test_guard_all_history_support(self):
        for masks in itertools.product(range(16),repeat=3):
            s=[[j for j in range(4) if m>>j&1] for m in masks]
            for issuer in range(4):
                self.assertTrue(all(r['support']>=2 for r in availability_trace(s,issuer,4,2,'guard_k')))

    def test_common_has_no_availability_identity_channel(self):
        masks=[[0,1,2],[1,2,3],list(range(4)),[0,2,3]]
        histories=[availability_trace(masks,j,4,3,'common') for j in range(4)]
        self.assertTrue(all([r['accepted'] for r in h]==[False,False,True,False] for h in histories))
        self.assertTrue(all(h[-1]['support']==4 for h in histories))

    def test_heartbeat_expiry_boundary(self):
        masks,pubs=heartbeat_masks(4,3,1,0,1,0)
        self.assertEqual(masks,[[0,1,2,3],[],[]])
        self.assertEqual(pubs,4)

    def test_no_outage_is_full_availability(self):
        masks,pubs=heartbeat_masks(4,90,0,.5,1,0)
        self.assertEqual(pubs,360)
        self.assertTrue(all(len(s)==4 for s in masks))


if __name__=='__main__':unittest.main(verbosity=2)
