"""Compare every logical feature, every trace field and every ordered summary."""
import csv
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'analysis'))
from inputs import synthetic, write_bars
from reference import replay

BINARY = os.environ.get('STRATEGY_BINARY')
MANUAL_BINARY = os.environ.get('STRATEGY_MANUAL_BINARY')
INTEGER_FIELDS = {'config', 'fast', 'slow', 'bar', 'target_long', 'opening_event', 'trades'}


def read(path):
    with path.open() as file:
        return list(csv.DictReader(file))


@unittest.skipUnless(BINARY, 'STRATEGY_BINARY is set by CTest')
class EngineParity(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def invoke(self, bars, spans, order='strategy', layout='history', count=None, extra=(), binary=BINARY):
        write_bars(self.root/'bars.csv', bars)
        prefix = self.root / (order+'-'+layout)
        command = [binary, '--bars', str(self.root/'bars.csv'), '--spans', ','.join(map(str, spans)),
                   '--layout', layout, '--order', order, '--output', str(prefix)]
        if count is not None:
            command += ['--count', str(count)]
        result = subprocess.run(command + list(extra), capture_output=True, text=True, timeout=30)
        return result, prefix

    def compare_rows(self, actual, expected):
        self.assertEqual(len(actual), len(expected))
        for index, (row, wanted) in enumerate(zip(actual, expected)):
            self.assertEqual(set(row), set(wanted))
            for key, value in wanted.items():
                got = int(row[key]) if key in INTEGER_FIELDS else float(row[key])
                if key in INTEGER_FIELDS:
                    self.assertEqual(got, value, (index, key))
                else:
                    self.assertTrue(math.isfinite(got))
                    self.assertTrue(math.isclose(got, value, rel_tol=2e-12, abs_tol=1e-9), (index, key, got, value))

    def check_case(self, bars, spans, count=None, fee=.0001):
        matrix, summaries, trace = replay(bars, spans, count, fee=fee)
        first = None
        for layout in ('history', 'snapshot'):
            for order in ('strategy', 'event'):
                extra = ['--trace', '--fee', str(fee)]
                if len(bars) <= max(spans):
                    extra.append('--allow-empty')
                result, prefix = self.invoke(bars, spans, order, layout, count, extra)
                self.assertEqual(result.returncode, 0, result.stderr)
                metadata = json.loads(result.stdout)
                self.assertFalse(metadata['timed'])
                self.assertEqual(metadata['whole_ns'], 0)
                self.assertEqual(metadata['eligible_bars'], max(0, len(bars)-max(spans)))
                self.compare_rows(read(Path(str(prefix)+'.summary.csv')), summaries)
                self.compare_rows(read(Path(str(prefix)+'.trace.csv')), trace)
                actual_features = read(Path(str(prefix)+'.features.csv'))
                self.assertEqual(len(actual_features), len(bars)*len(spans))
                for i, row in enumerate(actual_features):
                    t, w = divmod(i, len(spans))
                    self.assertEqual((int(row['bar']), int(row['window']), int(row['span'])), (t, w, spans[w]))
                    self.assertEqual(float(row['value']), matrix[t][w])
                payload = tuple(Path(str(prefix)+'.'+suffix+'.csv').read_bytes() for suffix in ('summary', 'trace', 'features'))
                if first is None:
                    first = payload
                self.assertEqual(payload, first, 'four C++ variants must be bit-for-bit equal')
                # Exercise the actual no-trace specialization separately.
                plain, _ = self.invoke(bars, spans, order, layout, count,
                                       [x for x in extra if x != '--trace'])
                self.assertEqual(plain.returncode, 0, plain.stderr)
                self.assertEqual(Path(str(prefix)+'.summary.csv').read_bytes(), payload[0])
                if MANUAL_BINARY:
                    # Same independent oracle and boundary fixtures, both trace and
                    # actual no-trace kernels. Compare serialized values exactly.
                    manual, _ = self.invoke(bars, spans, order, layout, count, extra,
                                            binary=MANUAL_BINARY)
                    self.assertEqual(manual.returncode, 0, manual.stderr)
                    manual_payload = tuple(Path(str(prefix)+'.'+suffix+'.csv').read_bytes()
                                           for suffix in ('summary', 'trace', 'features'))
                    self.assertEqual(manual_payload, payload, 'manual indexing must match mdspan exactly')
                    manual_plain, _ = self.invoke(bars, spans, order, layout, count,
                                                  [x for x in extra if x != '--trace'],
                                                  binary=MANUAL_BINARY)
                    self.assertEqual(manual_plain.returncode, 0, manual_plain.stderr)
                    self.assertEqual(Path(str(prefix)+'.summary.csv').read_bytes(), payload[0])

    def test_deterministic_boundary_accounts(self):
        for closes in ([100.]*8, [100.,110.,120.,80.,90.], [100.,110.,120.,102.],
                       [110.,105.,100.,95.,90.,85.], [100.,100.,100.,100.,150.,80.,160.,70.]):
            bars = [(t, 99. if t == 4 else 100., close) for t, close in enumerate(closes)]
            with self.subTest(closes=closes):
                self.check_case(bars, [2,3])
        self.check_case([(0,100.,100.)], [2,3])
        self.check_case([(i,100.,100.) for i in range(3)], [2,3])
        self.check_case(synthetic(12,11), [2,3,5], count=0)
        self.check_case(synthetic(12,11), [2], count=0)

    def test_odd_counts_common_warmup_and_seeded_histories(self):
        for seed in (11,29,47):
            with self.subTest(seed=seed):
                self.check_case(synthetic(65, seed), [2,3,5,9], count=5)
        self.check_case(synthetic(18, 17), [2,3,5], fee=0.)

    @unittest.skipUnless(os.environ.get('STRATEGY_HISTORICAL_CSV'), 'optional local historical fixture')
    def test_real_excerpts_including_overnight(self):
        rows=read(Path(os.environ['STRATEGY_HISTORICAL_CSV']))
        bars=[(int(r['timestamp']),float(r['open']),float(r['close'])) for r in rows]
        boundary=next(i for i in range(128,len(bars)-128) if bars[i][0]-bars[i-1][0]>60)
        for excerpt in (bars[:256],bars[boundary-128:boundary+128]):
            self.check_case(excerpt,list(range(2,97,2)),count=64)

    def test_current_close_cannot_change_current_opening(self):
        bars = synthetic(16, 11)
        changed = list(bars)
        changed[10] = (10, bars[10][1], bars[10][2]*3)
        snapshots = []
        for candidate in (bars, changed):
            result, prefix = self.invoke(candidate, [2,3], extra=['--trace'])
            self.assertEqual(result.returncode, 0, result.stderr)
            snapshots.append(next(row for row in read(Path(str(prefix)+'.trace.csv')) if row['bar']=='10'))
        for key in ('target_long','opening_event','cash_after_open','shares_after_open','opening_fee'):
            self.assertEqual(snapshots[0][key], snapshots[1][key])

    def test_invalid_inputs_are_rejected(self):
        good = [(i,100.,100.) for i in range(6)]
        cases = [(good, [], None, []), (good, [1,3], None, []), (good,[3,2],None,[]),
                 (good,[2,2],None,[]), (good,[2,3],2,[]), ([],[2,3],None,[]),
                 (good[:3],[2,3],None,[]), (good,[2,3],None,['--fee','1']),
                 (good,[2,3],None,['--fee','nan']), (good,[2,3],None,['--capital','0']),
                 (good,[2,3],None,['--capital','inf']), (good,[2,3],None,['--unknown','1']),
                 (good,[2,3],None,['--time','--trace'])]
        for bad in (0., -1., math.nan, math.inf):
            for column in (1,2):
                rows = [list(row) for row in good]
                rows[4][column] = bad
                cases.append((rows,[2,3],None,[]))
        cases.append(([(0,100.,100.),(0,100.,100.)], [2,3],None,['--allow-empty']))
        cases.append(([(1,100.,100.),(0,100.,100.)], [2,3],None,['--allow-empty']))
        for bars, spans, count, extra in cases:
            with self.subTest(spans=spans, extra=extra, bars=bars):
                result, _ = self.invoke(bars, spans, count=count, extra=extra)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('strategy_replay:', result.stderr)


if __name__ == '__main__':
    unittest.main()
