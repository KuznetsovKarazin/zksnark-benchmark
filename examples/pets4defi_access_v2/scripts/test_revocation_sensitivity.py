import csv
import tempfile
import unittest
from pathlib import Path

from revocation_model import DAY, EVENT_COSTS, validated_unit_costs
from revocation_sensitivity import access_grid, analyze, cache_trace, pair_grid, scenarios


def reference(accesses, updates, ttl, expiry):
    """Independent event queue, including simultaneous update/access/expiry."""
    events = [(t, 1, i) for i, t in enumerate(accesses)]
    events += [(t, 0, -1) for t in updates]
    epoch = 0; saved_epoch = -1; until = -1; full = []; rejected = []
    for now, kind, i in sorted(events):
        if kind == 0:
            epoch += 1
        elif now >= expiry:
            rejected.append(i)
        elif now >= until or saved_epoch != epoch:
            full.append(i); until = min(now + ttl, expiry); saved_epoch = epoch
    return full, rejected


class SensitivityTests(unittest.TestCase):
    def test_all_sensitivity_pairs_against_independent_event_queue(self):
        for name, config in scenarios():
            accesses = access_grid(config)
            for a, b in pair_grid(config['max_gap']):
                updates = [a*DAY, b*DAY]
                ttl = config['ttl_days']*DAY; expiry = config['expiry_days']*DAY
                actual = cache_trace(accesses, updates, ttl, expiry)
                expected = reference(accesses, updates, ttl, expiry)
                self.assertEqual((actual['full'], actual['rejected']), expected, (name,a,b))

    def test_expiry_rejects_and_cap_changes_writes_not_eligible_counts(self):
        accesses = [i*DAY for i in range(9)]
        short = cache_trace(accesses, [4*DAY,6*DAY], 3*DAY, 6*DAY)
        self.assertEqual(short['rejected'], [6,7,8])
        capped = cache_trace(accesses, [7*DAY], 3*DAY, 9*DAY)
        uncapped = cache_trace(accesses, [7*DAY], 3*DAY, 12*DAY)
        self.assertEqual(capped['full'],uncapped['full'])
        self.assertEqual(capped['deadline_changes']+1,uncapped['deadline_changes'])

    def test_cluster_law_and_reference_summary(self):
        self.assertEqual((len(pair_grid()),len(pair_grid(1)),len(pair_grid(7))),(3916,88,595))
        name,config=next(scenarios()); row,_=analyze(name,config,validated_unit_costs())
        self.assertEqual(row['count_distribution'],'{"3":6,"4":1675,"5":2235}')
        self.assertAlmostEqual(row['probability_zk_more_gas'],2235/3916)

    def test_gas_source_guard_detects_drift(self):
        validated_unit_costs()
        with EVENT_COSTS.open(newline='') as f:
            reader=csv.DictReader(f); fields=reader.fieldnames; rows=list(reader)
        for r in rows:
            if (r['policy'],r['variant'],r['event'])==('security','zk_cache','cache_reauthorize'):
                r['mean']=str(float(r['mean'])+1)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'event_costs.csv'
            with p.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
            with self.assertRaisesRegex(ValueError,'ZK_THREE'):
                validated_unit_costs(p)


if __name__=='__main__': unittest.main()
