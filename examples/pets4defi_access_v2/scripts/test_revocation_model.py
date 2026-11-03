import itertools
import math
import unittest
from collections import Counter, defaultdict

from revocation_model import (DAY, authorization_indices, fixed_count_distribution,
                              poisson_distribution, renewal_expectation)


def reference_count(days, n, step_days, ttl_days):
    """Independent event-driven cache with stored epoch and deadline."""
    events=sorted([(d,0) for d in days]+[(i*step_days,1) for i in range(n)])
    epoch=0; stored=None; deadline=-1; count=0
    for t,kind in events:
        if kind==0:
            epoch+=1
        elif stored!=epoch or t>=deadline:
            count+=1; stored=epoch; deadline=t+ttl_days
    return count


class ModelTests(unittest.TestCase):
    def test_exact_grid_against_independent_event_machine(self):
        for days in itertools.combinations(range(1,90),2):
            self.assertEqual(len(authorization_indices([d*DAY for d in days])),
                             reference_count(days,100,.9,30))

    def test_fixed_count_dp_against_exhaustive_subsets(self):
        days=list(range(1,10))
        result=fixed_count_distribution(5,n=11,step=DAY,ttl=3*DAY,candidate_days=days)
        for m in range(6):
            expected=Counter(reference_count(x,11,1,3) for x in itertools.combinations(days,m))
            self.assertEqual(result[m],expected)

    def test_multiple_updates_in_one_access_interval(self):
        days=list(range(1,10))
        result=fixed_count_distribution(3,n=5,step=3*DAY,ttl=5*DAY,candidate_days=days)
        for m in range(4):
            self.assertEqual(result[m],Counter(reference_count(x,5,3,5) for x in itertools.combinations(days,m)))

    def test_poisson_distribution_against_all_binary_interval_patterns(self):
        for rate in [0,.2,1,5]:
            p=1-math.exp(-rate); expected=defaultdict(float)
            for flags in itertools.product([0,1],repeat=7):
                days=[i+1 for i,x in enumerate(flags) if x]
                expected[reference_count(days,8,1,3)]+=p**sum(flags)*(1-p)**(7-sum(flags))
            actual=poisson_distribution(rate,n=8,step=DAY,ttl=3*DAY)
            for k in set(expected)|set(actual): self.assertAlmostEqual(actual.get(k,0),expected.get(k,0),places=12)
            mean=sum(k*v for k,v in expected.items())
            self.assertAlmostEqual(renewal_expectation(rate,n=8,step=DAY,ttl=3*DAY),mean,places=12)

    def test_hit_does_not_restart_ttl_and_boundary_event_coalesces(self):
        self.assertEqual(authorization_indices([],n=7,step=DAY,ttl=3*DAY),[0,3,6])
        self.assertEqual(authorization_indices([3*DAY],n=7,step=DAY,ttl=3*DAY),[0,3,6])


if __name__=='__main__': unittest.main()
