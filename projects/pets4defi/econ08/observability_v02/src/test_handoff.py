"""Economic invariants for the beneficiary-funded benchmark."""
import unittest
from fractions import Fraction
from build_handoff import beneficiary_transfers


class BeneficiaryTests(unittest.TestCase):
    def test_unequal_groups_pay_equal_premium_per_holder(self):
        groups = {1: dict(holders=1, common=110, selective=100),
                  2: dict(holders=3, common=390, selective=300)}
        tx = beneficiary_transfers(groups)
        self.assertEqual(tx[1], dict(premium=25, paid=15, received=0))
        self.assertEqual(tx[2], dict(premium=75, paid=0, received=15))
        for i, g in groups.items():
            net = g['common'] + tx[i]['paid'] - tx[i]['received']
            self.assertEqual((net - g['selective']) / g['holders'], 25)
        self.assertEqual(sum(g['common'] for g in groups.values()), 500)

    def test_symmetric_weekly_case_equals_self(self):
        groups = {i: dict(holders=1, common=10615258, selective=8022007)
                  for i in range(1, 5)}
        tx = beneficiary_transfers(groups)
        for s in tx.values():
            self.assertEqual(s, dict(premium=2593251, paid=0, received=0))

    def test_fractional_allocation_preserves_budget(self):
        groups = {1: dict(holders=1, common=2, selective=1),
                  2: dict(holders=2, common=2, selective=2)}
        tx = beneficiary_transfers(groups)
        self.assertEqual(tx[1]['premium'], Fraction(1, 3))
        self.assertEqual(tx[2]['premium'], Fraction(2, 3))
        self.assertEqual(sum(s['paid'] for s in tx.values()),
                         sum(s['received'] for s in tx.values()))

    def test_no_holder_is_invalid(self):
        with self.assertRaises(ValueError):
            beneficiary_transfers({1: dict(holders=0, common=0, selective=0)})


if __name__ == '__main__':
    unittest.main()
