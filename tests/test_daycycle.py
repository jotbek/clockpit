"""Local-time sky behaviour, clock jumps and bounded animation state."""
import calendar
import unittest
from unittest.mock import patch

from animations.mod_daycycle import DayCycle
from core.localtime import day_of_week, is_dst_poland, local_seconds


class LocalTimeTests(unittest.TestCase):
    def test_weekdays_and_dst_transition_dates(self):
        for year in range(2000, 2041):
            for month in (3, 10):
                for day in range(1, 32):
                    self.assertEqual(day_of_week(year, month, day),
                                     calendar.weekday(year, month, day))
                sunday = max(week[calendar.SUNDAY]
                             for week in calendar.monthcalendar(year, month))
                self.assertEqual(is_dst_poland(year, month, sunday, 0), month == 10)
                self.assertEqual(is_dst_poland(year, month, sunday, 1), month == 3)

    def test_polish_midnight_and_exact_dst_changes(self):
        cases = (
            ((2026, 1, 1, 23, 15, 0), 15 * 60),
            ((2026, 7, 1, 22, 15, 0), 15 * 60),
            ((2026, 3, 29, 0, 59, 59), 2 * 3600 - 1),
            ((2026, 3, 29, 1, 0, 0), 3 * 3600),
            ((2026, 10, 25, 0, 59, 59), 3 * 3600 - 1),
            ((2026, 10, 25, 1, 0, 0), 2 * 3600),
        )
        for utc, expected in cases:
            self.assertEqual(local_seconds(utc), expected)


class DayCycleTests(unittest.TestCase):
    def test_sun_moves_east_to_west_and_peaks_at_noon(self):
        cycle = DayCycle(16, 16)
        positions = [cycle._position(hour * 3600) for hour in (6, 9, 12, 15, 17)]
        self.assertTrue(all(position[0] for position in positions))
        self.assertEqual(sorted(p[1] for p in positions), [p[1] for p in positions])
        self.assertLess(positions[2][2], positions[1][2])
        self.assertLess(positions[2][2], positions[3][2])
        cycle._render(12 * 3600)
        brightest = max(range(256), key=lambda i: sum(cycle.frame[i * 3:i * 3 + 3]))
        x, y = divmod(brightest, 16)
        self.assertIn(x, (7, 8))
        self.assertLess(y, 5)

    def test_moon_crosses_midnight_on_a_continuous_arc(self):
        cycle = DayCycle(16, 16)
        evening, midnight, morning = (cycle._position(hour * 3600) for hour in (20, 0, 4))
        self.assertFalse(evening[0] or midnight[0] or morning[0])
        self.assertLess(evening[1], midnight[1])
        self.assertLess(midnight[1], morning[1])
        self.assertLess(midnight[2], evening[2])
        self.assertLess(midnight[2], morning[2])

    def test_twilight_and_midnight_have_no_frame_flash(self):
        cycle = DayCycle(16, 16)
        for second in (0, cycle.SUNRISE, cycle.SUNSET):
            cycle._render((second - 1) % 86400)
            before = bytes(cycle.frame)
            cycle._render((second + 1) % 86400)
            self.assertLessEqual(max(abs(a - b) for a, b in zip(before, cycle.frame)), 8)

    def test_full_day_reuses_buffers_at_multiple_resolutions(self):
        for width, height in ((16, 16), (7, 5), (1, 1)):
            cycle = DayCycle(width, height)
            frame, ridge = cycle.frame, cycle.ridge
            fields = set(vars(cycle))
            for second in range(0, 86400, 600):
                cycle._render(second)
                self.assertIs(cycle.frame, frame)
                self.assertIs(cycle.ridge, ridge)
                self.assertEqual(len(frame), width * height * 3)
                self.assertEqual(set(vars(cycle)), fields)

    def test_local_rtc_cache_and_backwards_clock_adjustment(self):
        cycle = DayCycle(16, 16)
        times = [(2026, 7, 1, 10, 0, 0)] * 2 + [
            (2026, 7, 1, 9, 59, 59), (2026, 7, 1, 22, 0, 0)]
        with patch('animations.mod_daycycle.time.localtime', side_effect=times), \
             patch('animations.mod_daycycle.time.time', side_effect=AssertionError('epoch float')), \
             patch.object(cycle, '_render', wraps=cycle._render) as render:
            for expected in (43200, 43200, 43199, 0):
                full, delay, frame = cycle.get()
                self.assertTrue(full)
                self.assertGreater(delay, 0)
                self.assertIs(frame, cycle.frame)
                self.assertEqual(cycle.last_second, expected)
            self.assertEqual(render.call_count, 3)

    def test_configurable_daylight_hours_and_validation(self):
        class ShortDay(DayCycle):
            SUNRISE = 8 * 3600
            SUNSET = 16 * 3600

        cycle = ShortDay(16, 16)
        self.assertFalse(cycle._position(7 * 3600)[0])
        self.assertTrue(cycle._position(12 * 3600)[0])
        self.assertFalse(cycle._position(17 * 3600)[0])
        for second in range(0, 86400, 1800):
            cycle._render(second)
        for resolution in ((0, 16), (16, 0), (-1, 16)):
            with self.assertRaises(ValueError):
                DayCycle(*resolution)


if __name__ == '__main__':
    unittest.main()
