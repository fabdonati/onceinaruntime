from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'analysis'))
from historical import CALENDAR, schedule, select_windows, validate_row


class HistoricalChecks(unittest.TestCase):
    def test_calendar_dst_half_days_and_exceptional_closure(self):
        sessions=schedule(json.loads(CALENDAR.read_text()))
        self.assertEqual(len(sessions),752)
        self.assertEqual(sum((b-a)//60 for a,b in sessions.values()),291840)
        self.assertNotIn('2025-01-09',sessions)
        self.assertNotIn('2024-07-04',sessions)
        self.assertNotIn('2024-03-10',sessions)
        self.assertEqual((sessions['2024-07-03'][1]-sessions['2024-07-03'][0])//60,210)
        for day,hour in [('2024-03-08',14),('2024-03-11',13)]:
            self.assertEqual(datetime.fromtimestamp(sessions[day][0],timezone.utc).hour,hour)

    def test_prices_and_minute_start_are_validated(self):
        good=dict(timestamp='60',timestamp_utc='1970-01-01T00:01:00Z',open='100',high='102',low='99',close='101',vwap='100.5',volume='10',trade_count='2')
        self.assertEqual(validate_row(good),(60,100.,101.))
        for key,value in [('timestamp','61'),('timestamp_utc','1970-01-01T00:02:00Z'),('open','nan'),('close','0'),('high','100'),('low','102'),('volume','inf'),('trade_count','0')]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                validate_row(dict(good,**{key:value}))

    def test_selection_uses_prices_with_deterministic_ties_and_nested_crops(self):
        bars=[(i*60,100.,100.) for i in range(26)]
        blocks,datasets=select_windows(bars,size=8,short=4)
        self.assertEqual(len(blocks),3)
        self.assertEqual([d['parent_block'] for d in datasets[::2]],[0,1,2])
        self.assertEqual([d['parent_offset'] for d in datasets[::2]],[0,2,2])
        self.assertTrue(all(d['offset']+d['bars']<=24 for d in datasets))
        for short,long in zip(datasets[::2],datasets[1::2]):
            self.assertGreaterEqual(short['start'],long['start'])
            self.assertLessEqual(short['end'],long['end'])
        with self.assertRaises(ValueError): select_windows(bars[:16],size=8,short=4)
