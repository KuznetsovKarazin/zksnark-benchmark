import itertools
import unittest
import numpy as np
from observers import hmm, anchored_predictions


def exhaustive_likelihood(obs, publications, issuer, activity, ttl, error, missing, rho):
    """Independent scalar enumeration of actual accesses and selected updates."""
    days=len(obs);total=0.
    probabilities=[]
    for day in range(days):
        own=publications[issuer,day]
        foreign=sum(publications[j,day] for j in range(len(publications)) if j!=issuer)
        probabilities.append(1. if own else 1-(1-rho)**foreign)
    for accesses in itertools.product((False,True),repeat=days):
        pa=np.prod([activity if a else 1-activity for a in accesses])
        for selected in itertools.product((False,True),repeat=days):
            ps=np.prod([p if bit else 1-p for bit,p in zip(selected,probabilities)])
            if not ps:continue
            likelihood=pa*ps;age=ttl;pending=False
            for day,(a,s,y) in enumerate(zip(accesses,selected,obs)):
                if day:age=min(ttl,age+1)
                pending=pending or s
                full=a and (age>=ttl or pending)
                if a and full:age=0;pending=False
                if y==-1:likelihood*=missing if a else 1
                elif not a:likelihood=0;break
                else:likelihood*=(1-missing)*((1-error) if bool(y)==full else error)
            total+=likelihood
    return total


class ObserverTests(unittest.TestCase):
    def test_hmm_matches_complete_latent_history_enumeration(self):
        u=np.array([[0,1,0,0],[0,0,1,0],[0,0,0,1]])
        prior=np.array([.2,.3,.5]);a=.6;e=.17;m=.3;rho=.4;ttl=2
        for obs in [[1,-1,0,1],[-1,0,-1,1],[0,1,1,-1]]:
            got=hmm(np.array([obs]),u,a,prior=prior,ttl=ttl,policy='cover',rho=rho,label_error=e,missing=m)[0]
            for t in range(1,5):
                weights=np.array([prior[j]*exhaustive_likelihood(obs[:t],u[:,:t],j,a,ttl,e,m,rho) for j in range(3)])
                np.testing.assert_allclose(got[t-1],weights/weights.sum(),rtol=1e-11,atol=1e-12)

    def test_no_issuer_signal_preserves_nonuniform_prior(self):
        u=np.tile(np.array([0,1,0,1,0]),(4,1));prior=np.array([.1,.2,.3,.4])
        got=hmm(np.array([[1,-1,0,1,0]]),u,.6,prior=prior,label_error=.1,missing=.3)
        np.testing.assert_allclose(got,np.tile(prior,(1,5,1)),atol=1e-12)

    def test_random_labels_carry_no_information(self):
        u=np.eye(4,dtype=int);prior=np.array([.1,.2,.3,.4])
        got=hmm(np.array([[1,-1,0,1]]),u,.6,prior=prior,label_error=.5,missing=.3)
        np.testing.assert_allclose(got,np.tile(prior,(1,4,1)),atol=1e-12)

    def test_consistent_permutation_is_invariance_not_null(self):
        u=np.eye(4,dtype=int);obs=np.array([[1,-1,0,1]]);prior=np.array([.1,.2,.3,.4]);perm=[2,0,3,1]
        a=hmm(obs,u,.6,prior=prior,label_error=.1,missing=.3)
        b=hmm(obs,u[perm],.6,prior=prior[perm],label_error=.1,missing=.3)
        np.testing.assert_allclose(a[:,:,perm],b,atol=1e-12)

    def test_chunk_size_does_not_change_posterior(self):
        obs=np.tile([1,-1,0,1],(7,1));u=np.eye(4,dtype=int)
        a=hmm(obs,u,.6,label_error=.1,missing=.3,chunk_size=2)
        b=hmm(obs,u,.6,label_error=.1,missing=.3,chunk_size=128)
        np.testing.assert_array_equal(a,b)

    def test_impossible_transcript_is_not_silently_smoothed(self):
        with self.assertRaises(ValueError):hmm(np.array([[0]]),np.zeros((4,1)),1.)

    def test_anchors_abstain_without_leaking_nonanchor_truth(self):
        np.testing.assert_array_equal(anchored_predictions([0,0,1,1,2],{0:7,2:3}),[7,7,3,3,-1])


if __name__=='__main__':unittest.main()
