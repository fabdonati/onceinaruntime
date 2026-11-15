import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'analysis'))
from run import ORDERS, STUDY, audit_rows, plan, validate_config


class CampaignChecks(unittest.TestCase):
    def test_balanced_positions_and_predecessors(self):
        self.assertEqual(len(set(ORDERS)),4)
        for position in range(4):
            self.assertEqual({row[position] for row in ORDERS},set(range(4)))
        pairs=[(a,b) for row in ORDERS for a,b in zip(row,row[1:])]
        self.assertEqual(len(set(pairs)),12)

    def test_frozen_matrix_and_nested_window_coverage(self):
        cfg=json.loads((STUDY/'configs/pilot.json').read_text())
        validate_config(cfg)
        self.assertEqual(len(plan(cfg,True)),192)
        self.assertEqual(len(plan(cfg,False)),48)
        pairs=[(f,s) for f in range(48) for s in range(f+1,48)]
        for count in cfg['counts']:
            self.assertEqual({w for pair in pairs[:count] for w in pair},set(range(48)))
        changed=copy.deepcopy(cfg); changed['repeats']=5
        with self.assertRaises(ValueError): validate_config(changed)

    def test_main_matrix_is_separate_and_balanced(self):
        cfg=json.loads((STUDY/'configs/main.json').read_text())
        validate_config(cfg)
        rows=plan(cfg,True)
        self.assertEqual(len(rows),576)
        self.assertEqual(len(plan(cfg,False)),72)
        for repetition in range(8):
            selected=[r for r in rows if (r['bars'],r['seed'],r['configs'],r['repeat'])==(4096,11,64,repetition)]
            self.assertEqual(len({(r['order'],r['layout']) for r in selected}),4)
        self.assertEqual(cfg['quiet_seconds'],60)
        self.assertLess(cfg['maximum_quiet_wait_seconds'],cfg['maximum_seconds'])

    def test_audit_rejects_order_count_and_invalid_numbers(self):
        good=[dict(config='0',fast='2',slow='3',trades='2',final_cash='1000')]
        self.assertEqual(audit_rows(good,good),0.)
        for key,value in (('config','1'),('trades','3'),('final_cash','nan'),('final_cash','1001')):
            bad=copy.deepcopy(good); bad[0][key]=value
            with self.assertRaises(ValueError): audit_rows(bad,good)
        with self.assertRaises(ValueError): audit_rows([],good)


if __name__=='__main__':
    unittest.main()
