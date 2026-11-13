import unittest
from liquidity_diagnostic import prefix_capital,serial_admission_floor,target_and_funding

def ev(t,g):return {'t':t,'gas':g}

class LiquidityTests(unittest.TestCase):
    def test_no_refill_is_total_not_schedule_peak(self):
        for times in [(0,1,2),(0,40,99)]:
            m=target_and_funding([ev(t,g) for t,g in zip(times,[3,5,2])],None,100)
            self.assertEqual((m['target'],m['gross_treasury_funding'],m['end_balance']),(10,10,0))
    def test_same_cost_timing_changes_refill_target(self):
        self.assertEqual(target_and_funding([ev(0,7),ev(9,7)],10,20)['target'],14)
        self.assertEqual(target_and_funding([ev(0,7),ev(10,7)],10,20)['target'],7)
    def test_tie_refill_precedes_debit(self):
        m=target_and_funding([ev(9,5),ev(10,7)],10,20)
        self.assertEqual((m['target'],m['refill_transfers'],m['end_balance']),(7,5,0))
    def test_replenishment_does_not_reduce_resource_or_total_funding(self):
        m=target_and_funding([ev(0,10),ev(11,2)],10,30)
        self.assertEqual(m['target'],10)
        self.assertEqual(m['total_debit'],12)
        self.assertEqual(m['gross_treasury_funding'],22)
        self.assertEqual(m['end_balance'],10)
        self.assertEqual(m['initial_transfer']+m['refill_transfers']-m['end_balance'],12)
    def test_empty_account(self):
        m=target_and_funding([],10,25)
        self.assertEqual((m['target'],m['total_debit'],m['gross_treasury_funding']),(0,0,0))
    def test_invalid_events_are_not_silently_clipped(self):
        for events in [[ev(-1,1)],[ev(20,1)],[ev(1,-1)]]:
            with self.assertRaises(ValueError):target_and_funding(events,10,20)
    def test_receipt_timing_changes_prefix_deficit(self):
        self.assertEqual(prefix_capital([5,-5,5]),5)
        self.assertEqual(prefix_capital([5,5,-5]),10)
        self.assertEqual(prefix_capital([-5,5]),0)
    def test_validation_requirement_exceeds_actual_spending(self):
        self.assertEqual(serial_admission_floor([2,2],[10,10]),12)
        self.assertEqual(prefix_capital([2,2]),4)
        with self.assertRaises(ValueError):serial_admission_floor([3],[2])
    def test_pooling_target_not_sum_of_unsynchronized_peaks(self):
        a=[ev(1,9),ev(11,1)];b=[ev(1,1),ev(11,9)]
        self.assertEqual(target_and_funding(a+b,10,20)['target'],10)
        self.assertEqual(sum(target_and_funding(x,10,20)['target'] for x in [a,b]),18)

if __name__=='__main__':unittest.main()
