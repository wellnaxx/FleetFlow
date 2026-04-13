import unittest
from datetime import datetime, timedelta, timezone

from src.core.serialization import dt_from_str, dt_to_str


class DateTimeSerialization_Should(unittest.TestCase):
    def test_none_roundtrip(self):
        self.assertIsNone(dt_to_str(None))
        self.assertIsNone(dt_from_str(None))
        self.assertIsNone(dt_from_str(""))

    def test_naive_datetime_to_str_preserves_wallclock(self):
        dt = datetime(2025, 9, 27, 14, 5, 6)  # naive
        s = dt_to_str(dt)
        self.assertEqual(s, "2025-09-27T14:05:06")
        # round-trip is naive and equal
        dt2 = dt_from_str(s)
        self.assertEqual(dt2, dt)
        assert dt2 is not None
        self.assertIsNone(dt2.tzinfo)

    def test_aware_datetime_is_converted_to_utc_and_naive(self):
        # 2025-09-27 15:05:06+02:00 should become 13:05:06 UTC
        aware = datetime(2025, 9, 27, 15, 5, 6, tzinfo=timezone(timedelta(hours=2)))
        s = dt_to_str(aware)
        self.assertEqual(s, "2025-09-27T13:05:06")  # UTC conversion + drop tz
        dt2 = dt_from_str(s)
        self.assertEqual(dt2, datetime(2025, 9, 27, 13, 5, 6))
        assert dt2 is not None
        self.assertIsNone(dt2.tzinfo)

    def test_microseconds_are_truncated(self):
        dt = datetime(2025, 1, 2, 3, 4, 5, 123456)  # has micros
        s = dt_to_str(dt)
        # No %f in ISO_FMT, so it should be truncated
        self.assertEqual(s, "2025-01-02T03:04:05")
        # parsing produces second precision only
        dt2 = dt_from_str(s)
        self.assertEqual(dt2, datetime(2025, 1, 2, 3, 4, 5))

    def test_parse_invalid_string_raises(self):
        with self.assertRaises(ValueError):
            dt_from_str("2025-09-27")  # missing time
        with self.assertRaises(ValueError):
            dt_from_str("not-a-datetime")
        with self.assertRaises(ValueError):
            dt_from_str("2025-09-27T13:05:06Z")  # 'Z' not in ISO_FMT
