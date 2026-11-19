"""Offline tests only; no credentials or Alpaca requests needed."""
import csv
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools' / 'alpaca'))
import download_qqq as downloader


def bar(instant='2023-01-03T14:30:00Z', close=101):
    return dict(t=instant, o=100, h=102, l=99, c=close, v=500, n=10, vw=100.5)


class DownloadChecks(unittest.TestCase):
    def test_date_coverage_and_dst(self):
        ranges = list(downloader.month_ranges(date(2023, 1, 1), date(2026, 1, 1)))
        self.assertEqual(len(ranges), 36)
        self.assertEqual(downloader.stamp(ranges[0][0]), '2023-01-01T05:00:00Z')
        self.assertEqual(downloader.stamp(ranges[-1][1]), '2026-01-01T05:00:00Z')
        self.assertEqual(downloader.stamp(ranges[2][1]), '2023-04-01T04:00:00Z')
        self.assertTrue(all(a[1] == b[0] for a, b in zip(ranges, ranges[1:])))

    def test_pagination_empty_page_identical_boundary_and_resume(self):
        first, second = bar(), bar('2023-01-03T14:31:00Z')
        pages = [dict(symbol='QQQ', bars=[first], next_page_token='a'),
                 dict(symbol='QQQ', bars=[], next_page_token='b'),
                 dict(symbol='QQQ', bars=[first, second], next_page_token=None)]
        queries = []
        def fetch(params):
            queries.append(params)
            return pages[len(queries)-1]
        start, end = next(downloader.month_ranges(date(2023, 1, 1), date(2023, 2, 1)))
        with tempfile.TemporaryDirectory() as folder:
            result = downloader.download_month(Path(folder), start, end, 'sip', 'split', fetch)
            self.assertEqual((result['rows'], result['pages'], result['identical_duplicates_skipped']), (2, 3, 1))
            self.assertEqual(queries[-1]['page_token'], 'b')
            self.assertEqual(queries[0]['end'], '2023-02-01T04:59:59.999999Z')
            self.assertEqual(downloader.download_month(Path(folder), start, end, 'sip', 'split',
                lambda _: self.fail('Resuming should not request downloaded months')), result)
            (Path(folder) / result['csv_file']).write_text('corrupted')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                downloader.download_month(Path(folder), start, end, 'sip', 'split', fetch)

    def test_repeated_token_and_conflicting_duplicate_rejected(self):
        start, end = next(downloader.month_ranges(date(2023, 1, 1), date(2023, 2, 1)))
        cases = [dict(symbol='QQQ', bars=[bar(), bar(close=100)], next_page_token=None),
                 dict(symbol='QQQ', bars=[bar()], next_page_token='repeat')]
        for payload in cases:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as folder:
                with self.assertRaises(ValueError):
                    downloader.download_month(Path(folder), start, end, 'sip', 'split', lambda _:payload)
                self.assertFalse((Path(folder) / '2023-01.json').exists())

    def test_invalid_prices_timestamps_and_interval_end_rejected(self):
        for change in [dict(o=0), dict(c=float('nan')), dict(c=200), dict(v=-1),
                       dict(t='2023-01-03T14:30:01Z'), dict(t='2023-01-03T14:30:00')]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                downloader.normalize(dict(bar(), **change))
        start, end = next(downloader.month_ranges(date(2023, 1, 1), date(2023, 2, 1)))
        with tempfile.TemporaryDirectory() as folder, self.assertRaisesRegex(ValueError, 'outside'):
            downloader.download_month(Path(folder), start, end, 'sip', 'split',
                lambda _:dict(symbol='QQQ', bars=[bar(downloader.stamp(end))]))

    def test_complete_export_has_canonical_projection_and_no_keys(self):
        with tempfile.TemporaryDirectory() as folder:
            argv = ['download_qqq.py', '--start', '2023-01-01', '--end', '2023-02-01', '--output', folder]
            with patch('sys.argv', argv), patch.dict('os.environ',
                  {'APCA_API_KEY_ID':'dummy-key', 'APCA_API_SECRET_KEY':'dummy-secret'}), \
                  patch.object(downloader, 'get_json', return_value=dict(symbol='QQQ', bars=[bar()], next_page_token=None)):
                downloader.main()
            output = Path(folder)
            state = json.loads((output/'manifest.json').read_text())
            self.assertEqual((state['status'], state['rows']), ('complete', 1))
            with (output/'QQQ_1Min_open_close.csv').open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(rows, [dict(timestamp='1672756200', open='100', close='101')])
            self.assertFalse((output/'.download.lock').exists())
            for path in output.rglob('*.json'):
                self.assertNotIn('dummy-key', path.read_text())
                self.assertNotIn('dummy-secret', path.read_text())


if __name__ == '__main__':
    unittest.main()
