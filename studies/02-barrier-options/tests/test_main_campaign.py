"""Campaign ordering, power refusal, data layout and integrity gates."""
import collections
import itertools
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

EXPERIMENT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENT / 'analysis'))
import run_main as campaign


class MainCampaignTests(unittest.TestCase):
    def setUp(self):
        self.cfg = json.loads((EXPERIMENT / 'configs/main.json').read_text())

    def test_complete_balanced_order_without_duplicate_observations(self):
        campaign.validate_config(self.cfg)
        plan = campaign.plan(self.cfg)
        self.assertEqual(len(plan), 324)
        self.assertEqual(len({r['id'] for r in plan}), 324)
        cases = collections.defaultdict(list)
        for r in plan:
            cases[r['seed'], r['barrier'], r['layout']].append(r)
        self.assertEqual(len(cases), 18)
        for rows in cases.values():
            orders = []
            for repeat in range(6):
                run = sorted((r for r in rows if r['repeat'] == repeat), key=lambda r: r['order_position'])
                orders.append(tuple(r['method'] for r in run))
            self.assertEqual(set(orders), set(itertools.permutations(('scalar', 'fixed', 'refill'))))
            self.assertEqual(len(orders), len(set(orders)))
            for method in self.cfg['methods']:
                positions = collections.Counter(r['order_position'] for r in rows if r['method'] == method)
                self.assertEqual(positions, {0: 2, 1: 2, 2: 2})

    def test_altered_workload_or_resource_budget_refused(self):
        for key, value in [('paths', 8192), ('process_repeats_per_seed_case', 7),
                           ('maximum_seconds', 3600), ('maximum_start_load_per_cpu', 1),
                           ('seeds', [11, 29]), ('maximum_evidence_bytes', 2 * campaign.GIB)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                campaign.validate_config(self.cfg | {key: value})

    def test_stable_ac_required_even_when_ac_is_detected(self):
        def record(text, code=0):
            return {'returncode': code, 'stdout': text}
        for state in ['charging', 'charged', 'finishing charge']:
            self.assertTrue(campaign.power_is_stable(record("Now drawing from 'AC Power'\n 83%; " + state)))
        for r in [record("Now drawing from 'AC Power'\n 8%; discharging"),
                  record("Now drawing from 'Battery Power'\n 83%; discharging"),
                  record("Now drawing from 'AC Power'\n 83%; unknown"),
                  record("Now drawing from 'AC Power'\n 83%; charged", 1), {'error': 'denied'}]:
            self.assertFalse(campaign.power_is_stable(r))

    def test_step_major_preserves_every_path_date_and_checks_dimensions(self):
        original = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12], [13, 14, 15]], dtype='<f8')
        with tempfile.TemporaryDirectory() as directory:
            canonical = Path(directory) / 'canonical.f64'
            output = Path(directory) / 'step.f64'
            original.tofile(canonical)
            metadata = campaign.step_major(canonical, output, 5, 3)
            actual = np.fromfile(output, dtype='<f8').reshape(3, 5)
            for p in range(5):
                for t in range(3):
                    self.assertEqual(actual[t, p], original[p, t])
            self.assertEqual(metadata['bytes'], 120)
            self.assertEqual(metadata['sha256'], campaign.digest(output))
            with self.assertRaises(ValueError):
                campaign.step_major(canonical, output, 4, 3)

    def test_storage_and_memory_estimates_fit_the_agreed_caps(self):
        e = campaign.estimates(self.cfg)
        self.assertEqual(e['retained_canonical_bytes'], 604800000)
        self.assertEqual(e['reference_bytes'], 15300000)
        self.assertLess(e['estimated_peak_evidence_bytes'], self.cfg['maximum_evidence_bytes'])
        self.assertLess(e['estimated_combined_peak_rss_bytes'], self.cfg['maximum_combined_peak_rss_bytes'])

    def test_unavailable_or_nonrelease_build_is_not_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            build = Path(directory)
            self.assertTrue(campaign.build_issues(build))
            (build / 'CMakeCache.txt').write_text('CMAKE_BUILD_TYPE:STRING=Debug\nMEASURED_SANITIZERS:BOOL=ON\n')
            self.assertTrue(any('Release' in issue for issue in campaign.build_issues(build)))
            self.assertTrue(any('SANITIZERS' in issue for issue in campaign.build_issues(build)))

    def test_whole_observation_identity_phase_sum_and_checksums(self):
        item = {'seed': 11, 'barrier': 120, 'layout': 'path', 'method': 'fixed'}
        valid = item | {'paths': 100000, 'steps': 252, 'validated': True, 'price': 2.5,
                        'generation_ns': 10, 'layout_ns': 1, 'output_allocation_bridge_compute_ns': 3,
                        'complete_ns': 14, 'canonical_sha256': 'canonical',
                        'layout_sha256': 'layout', 'payoffs_sha256': 'payoffs'}
        campaign.check_complete(valid, item, self.cfg, 'canonical', 'layout', 'payoffs')
        for key, value in [('complete_ns', 15), ('generation_ns', -1), ('validated', False),
                           ('paths', 99999), ('seed', 29), ('layout_sha256', 'wrong'),
                           ('payoffs_sha256', 'wrong'), ('price', float('nan'))]:
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                campaign.check_complete(valid | {key: value}, item, self.cfg, 'canonical', 'layout', 'payoffs')


if __name__ == '__main__':
    unittest.main()
