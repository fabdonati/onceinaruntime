import math
from fractions import Fraction
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'analysis'))
from reference import account, features, replay


class HandWorkedAccounting(unittest.TestCase):
    def test_ema_has_hand_computed_initial_values(self):
        actual = features([(0, 100., 100.), (1, 110., 110.), (2, 120., 120.)], [2, 3])
        expected = [(100, 100), (Fraction(320, 3), 105), (Fraction(1040, 9), Fraction(225, 2))]
        for row, wanted in zip(actual, expected):
            for value, correct in zip(row, wanted):
                self.assertAlmostEqual(value, float(correct), places=12)

    def test_fee_free_gap_and_close_only_drawdown(self):
        bars = [(0, 100., 100.), (1, 100., 110.), (2, 100., 120.), (3, 100., 80.), (4, 99., 90.)]
        _, summaries, trace = replay(bars, [2, 3], fee=0.)
        self.assertEqual([x['opening_event'] for x in trace], [1, -1])
        self.assertEqual([x['equity'] for x in trace], [800., 990.])
        self.assertEqual(summaries[0]['final_cash'], 990.)
        self.assertEqual(summaries[0]['trades'], 2)
        self.assertAlmostEqual(summaries[0]['max_drawdown'], .2)
        self.assertEqual(summaries[0]['turnover'], 1.99)

    def test_exact_fractional_fee_ledger(self):
        bars = [(0, 100., 100.), (1, 100., 102.)]
        summary, trace = account(bars, [True, False], 1)
        quantity = Fraction(1000, 1) / (100 * (1 + Fraction(1, 10000)))
        cash = quantity * 102 * (1 - Fraction(1, 10000))
        fees = quantity * (100 + 102) / 10000
        self.assertAlmostEqual(trace[0]['shares_after_open'], float(quantity), places=12)
        self.assertAlmostEqual(summary['final_cash'], float(cash), places=10)
        self.assertAlmostEqual(summary['fees'], float(fees), places=12)
        self.assertEqual(summary['trades'], 2)
        self.assertEqual(summary['max_drawdown'], 0.)

    def test_final_fee_replaces_mark_and_peak(self):
        # Gross last mark is 1000. Final fee leaves a loss; it must affect MDD.
        summary, trace = account([(0, 100., 100.), (1, 100., 100.)], [True, True], 1)
        expected = 1000 * (1 - .0001) / (1 + .0001)
        self.assertAlmostEqual(summary['final_cash'], expected)
        self.assertAlmostEqual(summary['max_drawdown'], 1 - expected / 1000)
        self.assertEqual(trace[0]['peak'], 1000.)
        self.assertEqual(trace[0]['shares'], 0.)

    def test_article_account_and_summary_only_reference(self):
        bars = [(i, 99. if i == 4 else 100., close)
                for i, close in enumerate([100.,120.,110.,102.,100.])]
        _, summaries, trace = replay(bars, [2,3], fee=0.)
        self.assertEqual([row['equity'] for row in trace], [1020.,990.])
        self.assertAlmostEqual(summaries[0]['max_drawdown'], 1 - 990/1020)
        matrix, no_trace, empty = replay(bars, [2,3], fee=0., diagnose=False)
        self.assertEqual(no_trace, summaries)
        self.assertFalse(empty)

    def test_same_target_does_not_rebalance(self):
        summary, trace = account([(i, 100., 100.+i) for i in range(5)], [True]*5, 1)
        self.assertEqual(summary['trades'], 2)
        self.assertEqual([x['opening_event'] for x in trace], [1, 0, 0, 0])
        self.assertEqual(len({x['shares_after_open'] for x in trace}), 1)

    def test_equality_and_common_warmup(self):
        bars = [(i, 100., 100.) for i in range(8)]
        _, summaries, trace = replay(bars, [2, 3, 5])
        self.assertEqual(len(trace), 9)
        self.assertEqual([x['bar'] for x in trace], [5, 6, 7]*3)
        self.assertTrue(all(x['trades'] == 0 and x['final_cash'] == 1000 for x in summaries))

    def test_no_eligible_bars_or_configurations(self):
        bars = [(0, 100., 100.), (1, 100., 100.)]
        _, summaries, trace = replay(bars, [2, 3])
        self.assertEqual(summaries[0]['final_cash'], 1000.)
        self.assertFalse(trace)
        _, summaries, trace = replay(bars, [2, 3], count=0)
        self.assertFalse(summaries or trace)


if __name__ == '__main__':
    unittest.main()
