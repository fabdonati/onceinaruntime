"""Numerical counterexamples for the post-campaign analysis (not timing tests)."""
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('main_views', Path(__file__).parents[1] / 'analysis/main_views.py')
V = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V)


class AnalysisTests(unittest.TestCase):
    def test_mean_stack_does_not_add_independent_medians(self):
        rows = [dict(generation_ns=g, layout_ns=0,
                     output_allocation_bridge_compute_ns=c, complete_ns=g+c)
                for g, c in ((1, 90), (2, 2), (90, 1))]
        result = V.mean_phases(rows)
        self.assertEqual(result['complete_mean_ms'], 62e-6)
        self.assertEqual(result['generation_mean_ms'], 31e-6)
        self.assertEqual(result['valuation_mean_ms'], 31e-6)
        rows[0]['complete_ns'] += 1
        with self.assertRaises(ValueError):
            V.mean_phases(rows)

    def test_final_date_hit_differs_from_maturity_survival(self):
        counts = V.survival_counts([1, 2, 252, 252], [1, 1, 1, 0], 252)
        self.assertEqual([int(counts[d]) for d in (0, 1, 2, 251, 252)], [4, 3, 2, 2, 1])
        self.assertTrue(all(a >= b for a, b in zip(counts, counts[1:])))

    def test_repeated_runs_do_not_multiply_unique_lane_work(self):
        rows = []
        for seed, useful in ((11, 2), (29, 4), (47, 6)):
            rows.extend(dict(seed=seed, barrier=120, method='fixed',
                             useful_lane_steps=useful, available_lane_steps=8,
                             replacements=0) for _ in range(12))
        work = V.pooled_work(rows, 120, 'fixed')
        self.assertEqual((work['useful'], work['available'], work['occupancy']), (12, 24, .5))
        rows[-1]['useful_lane_steps'] += 1
        with self.assertRaises(ValueError):
            V.pooled_work(rows, 120, 'fixed')

    def test_median_of_matched_changes_is_not_change_of_medians(self):
        # Matching can give a different result from comparing marginal medians.
        candidate, baseline = (4, 5, 100), (1, 10, 20)
        self.assertEqual(V.summary(V.matched_effect(a, b) for a, b in zip(candidate, baseline))['median'], 300.)
        self.assertEqual(V.matched_effect(V.summary(candidate)['median'], V.summary(baseline)['median']), -50.)


if __name__ == '__main__':
    unittest.main()
