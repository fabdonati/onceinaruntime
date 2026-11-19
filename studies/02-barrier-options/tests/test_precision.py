"""Counterexamples for precision reference, error metrics, and campaign identity."""
import copy
import json
from decimal import Decimal, localcontext
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'analysis'))
from model import oracle
from precision_model import errors, oracle32, ordered_mean
from run_precision import audit, check_observation, execution_plan, validate_config
from analyze_precision import paired_changes


class PrecisionTests(unittest.TestCase):
    def config(self):
        return json.loads((Path(__file__).resolve().parents[1]/'configs/precision-pilot.json').read_text())

    def test_literal_reference_and_decimal(self):
        factors=np.array([[2,.5,1],[1,1,2],[1,1,1],[.5,1,1],[1.25,1,1],[1,2.5,.5],[1,1.5,1]],dtype=np.float32)
        ref=oracle32(factors,16,.5,8,6)
        self.assertEqual(ref[0].tolist(),[0,0,1,0,2,0,3])
        self.assertEqual(ref[1].tolist(),[1,3,3,3,3,2,3])
        self.assertEqual(ref[2].tolist(),[1,1,0,0,0,1,0])
        with localcontext() as c:
            c.prec=60
            for row,actual in zip(factors,ref[0]):
                stock=Decimal(8);hit=False
                for f in row:
                    stock*=Decimal.from_float(float(f));hit|=stock>=16
                expected=Decimal(0) if hit else Decimal('.5')*max(stock-6,Decimal(0))
                self.assertEqual(float(actual),float(expected))

    def test_initial_and_final_hit_are_distinct_from_maturity(self):
        factors=np.array([[1,2],[1,1]],dtype=np.float32)
        ref=oracle32(factors,16,1,8,6)
        self.assertEqual(ref[1].tolist(),[2,2])
        self.assertEqual(ref[2].tolist(),[1,0])
        initial=oracle32(factors,8,1,8,6)
        self.assertEqual(initial[0].tolist(),[0,0])
        self.assertEqual(initial[1].tolist(),[0,0])

    def test_input_rounding_changes_classification(self):
        factors=np.array([[1.5-2**-25,1]],dtype=np.float64)
        double=oracle(factors,12,1,8,6)
        single=oracle32(factors,12,1,8,6)
        quantised=oracle(factors.astype(np.float32).astype(np.float64),12,1,8,6)
        self.assertEqual(double[2].tolist(),[0])
        self.assertEqual(single[2].tolist(),[1])
        self.assertEqual(quantised[2].tolist(),[1])
        metrics=errors(single,double)
        self.assertEqual(metrics['candidate_only_knockouts'],1)
        self.assertEqual(metrics['zero_payoff_disagreements'],1)
        self.assertLess(metrics['price_difference'],0)

    def test_float_rounds_each_update_and_payoff(self):
        # Exact float32 operands multiplied in float64 have an exact product;
        # rounding that product back independently checks binary32 updates.
        factors=np.array([[1.00001]*252,[.99999]*252],dtype=np.float32)
        reference=oracle32(factors,np.inf)
        expected=[]
        for row in factors:
            stock=np.float32(100)
            for value in row:
                stock=np.float32(float(stock)*float(value))
            intrinsic=np.float32(float(stock)-100.)
            intrinsic=max(intrinsic,np.float32(0))
            expected.append(np.float32(float(intrinsic)*float(np.float32(np.exp(-.02)))))
        np.testing.assert_array_equal(reference[0],expected)
        self.assertEqual(reference[0].dtype,np.dtype('float32'))

    def test_error_metrics_do_not_hide_cancellation(self):
        expected=(np.array([10.,10.,0.]),np.array([2,2,1]),np.array([0,0,1],dtype='u1'))
        actual=(np.array([11.,9.,0.],dtype='f4'),np.array([2,2,1]),np.array([0,0,1],dtype='u1'))
        metrics=errors(actual,expected)
        self.assertEqual(metrics['price_difference'],0)
        self.assertEqual(metrics['maximum_absolute_payoff_error'],1)
        self.assertAlmostEqual(metrics['rms_payoff_error'],np.sqrt(2/3))
        self.assertGreater(metrics['paired_difference_standard_error'],0)
        empty=tuple(np.array([],dtype=a.dtype) for a in actual)
        self.assertIsNone(errors(empty,empty)['paired_difference_standard_error'])

    def test_ordered_double_reduction(self):
        # A float32 reduction loses these small positive terms; FP64 order keeps them.
        values=np.array([2**24,1,1],dtype='f4')
        self.assertEqual(ordered_mean(values),(2**24+2)/3)

    def test_order_has_each_candidate_in_each_position(self):
        cfg=self.config();validate_config(cfg);plan=execution_plan(cfg)
        self.assertEqual(len(plan),648)
        self.assertEqual(len({p['id'] for p in plan}),648)
        for seed in cfg['seeds']:
            for barrier in cfg['barriers']:
                for layout in cfg['layouts']:
                    for precision in cfg['precisions']:
                        for method in cfg['methods']:
                            positions=[x['order_position'] for x in plan if (x['seed'],x['barrier'],x['layout'],x['precision'],x['method'])==(seed,barrier,layout,precision,method)]
                            self.assertEqual(sorted(positions),list(range(6)))
        wrong=copy.deepcopy(cfg);wrong['paths']=100000
        with self.assertRaises(ValueError):validate_config(wrong)

    def test_audit_and_observation_reject_hidden_mismatches(self):
        reference=(np.array([1,2],dtype='f4'),np.array([3,3],dtype='<u8'),np.array([0,0],dtype='u1'))
        cfg=dict(paths=2,steps=3)
        item=dict(precision='f32',method='fixed',layout='step',barrier=120)
        actual=item|dict(paths=2,steps=3,timed=False,validated_cpp=True,prepared_ns=0,price=1.5,input_bytes=24)
        check_observation(actual,item,cfg,reference,False)
        for key,value in [('price',1.6),('precision','f64'),('timed',True),('input_bytes',48),('prepared_ns',3)]:
            with self.assertRaises(RuntimeError):check_observation(actual|{key:value},item,cfg,reference,False)
        with tempfile.TemporaryDirectory() as directory:
            prefix=Path(directory)/'case'
            for suffix,values in zip(('payoffs.f32','lifetimes.u64','knocked.u8'),reference):
                values.tofile(str(prefix)+'.'+suffix)
            self.assertEqual(len(audit(prefix,'f32',reference)),3)
            np.array([2,1],dtype='f4').tofile(str(prefix)+'.payoffs.f32')
            with self.assertRaises(RuntimeError):audit(prefix,'f32',reference)

    def test_runtime_pairs_use_same_seed_repeat_and_correct_denominator(self):
        rows=[]
        for repeat,d,f in [(0,100,50),(1,200,300)]:
            for precision,duration in [('f64',d),('f32',f)]:
                rows.append(dict(seed=11,barrier=120,layout='path',repeat=repeat,method='fixed',precision=precision,
                                 id=f'{repeat}-{precision}',timed=True,prepared_ns=duration))
        changes=paired_changes(rows)
        self.assertEqual([r['change_percent'] for r in changes],[-50.,50.])
        self.assertEqual(paired_changes([r|dict(timed=False,prepared_ns=0) for r in rows]),[])
        with self.assertRaises(ValueError):paired_changes(rows+[rows[0]])
        with self.assertRaises(ValueError):paired_changes(rows[:-1])
        with self.assertRaises(ValueError):paired_changes([rows[0],rows[1]|dict(timed=False)])


if __name__=='__main__':unittest.main()
