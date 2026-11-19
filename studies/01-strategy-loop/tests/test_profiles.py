import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'analysis'))
from profiles import activity, describe
from reference import account


class ActivityChecks(unittest.TestCase):
    def test_hand_worked_openings_and_censored_end(self):
        # Eligible opens use targets 1..6: long,long,flat,long,flat,long.
        result=activity([False,True,True,False,True,False,True,False],2,block_size=4)
        self.assertEqual(result['changes'],5)
        self.assertEqual(result['held_bars'],4)
        self.assertEqual(result['completed'],[2,1])
        self.assertEqual(result['censored'],[1])
        self.assertEqual(result['blocks'],[dict(start_bar=2,bars=4,changes=3),dict(start_bar=6,bars=2,changes=2)])

    def test_matches_ledger_excluding_terminal_liquidation(self):
        bars=[(i,100.,100.) for i in range(9)]
        for targets in ([False]*9,[True]*9,[bool(i%2) for i in range(9)]):
            with self.subTest(targets=targets):
                a=activity(targets,2)
                _,trace=account(bars,targets,2)
                self.assertEqual(a['changes'],sum(r['opening_event']!=0 for r in trace))
                self.assertEqual(a['held_bars'],sum(r['shares_after_open']>0 for r in trace))

    def test_flat_prices_and_normalization(self):
        result=describe([(i,100.,100.) for i in range(10)],[2,3,4],counts=(1,3))
        for row in result['aggregates']:
            self.assertEqual(row['strategy_bars'],row['configs']*6)
            self.assertEqual(row['changes_per_1000'],0)
            self.assertEqual(row['long_fraction'],0)
            self.assertEqual(row['holding_bars'],dict(q1=None,median=None,q3=None))
