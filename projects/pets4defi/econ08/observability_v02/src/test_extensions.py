import unittest
from model import generate,infer,one_coin_probabilities,coin_likelihood_enumeration
from extensions import anonymous_features,average_linkage,adjusted_rand,auc_with_ties,cluster_metrics


class ExtensionTests(unittest.TestCase):
    def test_coin_skip_is_never_retried(self):
        updates=[{'at':1,'issuer':1}]
        obs=generate([0,2,3,4,5],updates,0,ttl=100,policy='one_coin',rho=.5,seed=0)
        self.assertEqual([r['refresh'] for r in obs],[True,False,False,False,False])

    def test_hit_conditions_old_coin_to_zero(self):
        lists=[[],[1],[],[]]
        self.assertEqual(one_coin_probabilities(3,0,2,100,0,lists,[1],0,.75),(0.,1.))

    def test_new_foreign_coin_after_skipped_one(self):
        lists=[[],[1,3],[],[]]
        self.assertEqual(one_coin_probabilities(4,0,2,100,0,lists,[1,3],0,.75),(.75,.25))

    def test_multiple_foreign_events_one_refresh(self):
        lists=[[],[1,2],[],[]]
        self.assertEqual(one_coin_probabilities(3,0,None,100,0,lists,[1,2],0,.5),(.75,.25))

    def test_coin_grace_publication_absorbed(self):
        updates=[{'at':1,'issuer':1}]
        # TTL at day 2 absorbs the publication before its day 4 deadline.
        obs=generate([0,2,3,4],updates,0,ttl=2,delta=3,policy='one_coin',rho=1)
        self.assertEqual([r['refresh'] for r in obs],[True,True,False,True])

    def test_tiny_hit_likelihood_not_lost(self):
        pubs=list(range(1,31));lists=[[],pubs,[],[]]
        full,hit=one_coin_probabilities(31,0,None,100,0,lists,pubs,0,.95)
        self.assertGreater(hit,0);self.assertAlmostEqual(hit/(.05**30),1,places=10)

    def test_coin_nonuniform_posterior(self):
        updates=[{'at':1,'issuer':0}]
        obs=[{'at':0,'refresh':True},{'at':2,'refresh':True}]
        p=infer(obs,updates,ttl=100,policy='one_coin',rho=.5,prior=[.7,.1,.1,.1])[-1]['posterior']
        self.assertAlmostEqual(p[0],.7/.85)

    def test_anonymous_attacker_rejects_issuer_labels(self):
        with self.assertRaises(ValueError):anonymous_features([], [{'at':1,'issuer':0}],100,0)

    def test_anonymous_attacker_rejects_holder_truth(self):
        with self.assertRaises(ValueError):anonymous_features([{'handle':'H','issuer':0,'observations':[]}],[],100,0)

    def test_missing_opportunity_is_not_a_hit(self):
        records=[{'handle':'H','observations':[{'at':0,'refresh':True},{'at':4,'refresh':True}]}]
        self.assertEqual(anonymous_features(records,[{'at':1},{'at':2}],100,0),[[None,None]])

    def test_ttl_expiry_is_not_issuer_response(self):
        records=[{'handle':'H','observations':[{'at':0,'refresh':True},{'at':4,'refresh':True}]}]
        self.assertEqual(anonymous_features(records,[{'at':3}],3,0),[[None]])

    def test_perfect_clusters_and_anchor(self):
        features=[[1,0],[1,0],[0,1],[0,1]]
        labels,dist,_=average_linkage(features,2)
        metrics=cluster_metrics([0,0,1,1],labels,dist)
        self.assertEqual(metrics['ari'],1);self.assertEqual(metrics['pair_auc'],1)
        self.assertEqual(metrics['anchor_assigned'],1);self.assertEqual(metrics['anchor_correct'],1)

    def test_auc_ties_are_uninformative(self):
        self.assertEqual(auc_with_ties([1,1,1,1],[0,1,0,1]),.5)

    def test_ari_ignores_cluster_names(self):
        self.assertEqual(adjusted_rand([0,0,1,1],[5,5,3,3]),1)


if __name__=='__main__':unittest.main()
