import unittest
from analyze import recurrence, funding, metrics, DAY

class Boundaries(unittest.TestCase):
    def test_ttl_is_exclusive(self):
        r=recurrence([0,9,10,11],[],10,0,30)
        self.assertEqual([x['event'] for x in r],['first','hit','reauthorize','hit'])
        self.assertEqual(r[2]['reason'],'AuthorizationExpired')

    def test_second_update_cannot_extend_deadline(self):
        r=recurrence([0,7,8,9],[5,7],30,3,40)
        self.assertEqual([x['event'] for x in r],['first','hit','reauthorize','hit'])
        self.assertEqual(r[2]['reason'],'StaleAuthorization')

    def test_publication_precedes_authorization_at_tie(self):
        r=recurrence([0,5,6],[5],30,0,40)
        self.assertEqual([x['event'] for x in r],['first','reauthorize','hit'])

    def test_expiry_reason_has_priority_at_joint_deadline(self):
        r=recurrence([0,10],[5],10,5,30)
        self.assertEqual(r[1]['reason'],'AuthorizationExpired')

    def test_long_grace_can_be_cut_off_by_ttl(self):
        r=recurrence([0,8,9],[5],8,20,40)
        self.assertEqual([x['event'] for x in r],['first','reauthorize','hit'])

    def test_refill_before_boundary_debit_and_terminal_balance(self):
        ev=[{'t':0,'gas':5},{'t':9,'gas':3},{'t':10,'gas':7},{'t':29,'gas':2}]
        f=funding(ev,10,0,0,30)
        self.assertEqual((f['K'],f['C'],f['T'],f['G'],f['E']),(8,17,15,23,6))

    def test_phase_and_stage_keep_original_calendar(self):
        ev=[{'t':5,'gas':4},{'t':6,'gas':7},{'t':15,'gas':3},{'t':16,'gas':5}]
        self.assertEqual(funding(ev,10,6,0,30)['bins'],[4,10,5,0])
        self.assertEqual(funding(ev,10,6,10,30)['bins'],[3,5,0])

    def test_no_refill_equals_expenditure(self):
        f=funding([{'t':2,'gas':10},{'t':5,'gas':2}],None,0,0,10)
        self.assertEqual((f['K'],f['T'],f['E']),(12,0,0))

    def test_pooling_noncoincident_maxima(self):
        ev=[{'t':0,'gas':10,'actor':'holder_0'},{'t':DAY,'gas':10,'actor':'holder_1'}]
        m=metrics(ev,DAY)
        self.assertEqual((m['pool_K'],m['SELF_sum_K'],m['pooling_reduction']),(10,20,10))

if __name__=='__main__':unittest.main()
