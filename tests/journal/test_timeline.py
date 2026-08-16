# Copyright (C) 2026, Sugar Labs (Shubham Sharma)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import time
import unittest

try:
    # cairo and gi (pulled in transitively by jarabe.journal.timeline via
    # sugar3.graphics.style) are apt-installed system packages, not
    # something a bare venv necessarily has -- skip rather than error
    # when they are not importable.
    import cairo
    import gi
    assert gi
except (ImportError, ValueError):
    raise unittest.SkipTest('gi is not available')

# jarabe/__init__.py and jarabe/journal/__init__.py are both gi-free, but
# jarabe isn't on sys.path outside a built/installed tree.
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from jarabe.journal import timeline  # noqa: E402


def _at_hour(hour):
    # band_kind reads time.localtime().tm_hour, so the fixed date only
    # needs to avoid DST edges; the hour is what matters.
    return time.mktime((2026, 8, 15, hour, 0, 0, 0, 0, -1))


def _assert_bbox_approx(actual, expected, abs_tol=0.01):
    for got, want in zip(actual, expected):
        assert abs(got - want) <= abs_tol, (actual, expected)


# --- safe_timestamp ---

class SafeTimestampTest(unittest.TestCase):

    def test_safe_timestamp_valid_number(self):
        self.assertEqual(timeline.safe_timestamp(1234567890), 1234567890.0)

    def test_safe_timestamp_valid_numeric_string(self):
        self.assertEqual(timeline.safe_timestamp('123.5'), 123.5)

    def test_safe_timestamp_none_uses_default(self):
        self.assertEqual(timeline.safe_timestamp(None), 0.0)
        self.assertEqual(timeline.safe_timestamp(None, default=42.0), 42.0)

    def test_safe_timestamp_nan_uses_default(self):
        self.assertEqual(timeline.safe_timestamp(float('nan')), 0.0)

    def test_safe_timestamp_infinities_use_default(self):
        self.assertEqual(timeline.safe_timestamp(float('inf')), 0.0)
        self.assertEqual(timeline.safe_timestamp(float('-inf')), 0.0)

    def test_safe_timestamp_non_numeric_string_uses_default(self):
        self.assertEqual(timeline.safe_timestamp('not-a-number'), 0.0)

    def test_safe_timestamp_out_of_localtime_range_uses_default(self):
        # Far enough outside the epoch that time.localtime() raises
        # (OverflowError on this platform); safe_timestamp must swallow it.
        self.assertEqual(timeline.safe_timestamp(10 ** 18), 0.0)


# --- band_kind ---

class BandKindTest(unittest.TestCase):

    # NOTE: the original test_band_kind_hour_boundaries was a single
    # @pytest.mark.parametrize'd function over 10 (hour, expected)
    # cases. pytest and unittest both count each parametrize case as
    # its own collected test, but a self.subTest() loop does not --
    # it stays one collected test under unittest and reports as
    # "N passed, 10 subtests passed" under pytest, so it cannot hit
    # the required 41/35/15 counts. Expanded to one method per case,
    # named for its (hour, expected) pair to keep the split traceable
    # back to the original parametrize table.

    def test_band_kind_hour_boundaries_00_early_hours(self):
        self.assertEqual(timeline.band_kind(_at_hour(0)), 'early_hours')

    def test_band_kind_hour_boundaries_04_early_hours(self):
        self.assertEqual(timeline.band_kind(_at_hour(4)), 'early_hours')

    def test_band_kind_hour_boundaries_05_morning(self):
        self.assertEqual(timeline.band_kind(_at_hour(5)), 'morning')

    def test_band_kind_hour_boundaries_11_morning(self):
        self.assertEqual(timeline.band_kind(_at_hour(11)), 'morning')

    def test_band_kind_hour_boundaries_12_afternoon(self):
        self.assertEqual(timeline.band_kind(_at_hour(12)), 'afternoon')

    def test_band_kind_hour_boundaries_16_afternoon(self):
        self.assertEqual(timeline.band_kind(_at_hour(16)), 'afternoon')

    def test_band_kind_hour_boundaries_17_evening(self):
        self.assertEqual(timeline.band_kind(_at_hour(17)), 'evening')

    def test_band_kind_hour_boundaries_20_evening(self):
        self.assertEqual(timeline.band_kind(_at_hour(20)), 'evening')

    def test_band_kind_hour_boundaries_21_night(self):
        self.assertEqual(timeline.band_kind(_at_hour(21)), 'night')

    def test_band_kind_hour_boundaries_23_night(self):
        self.assertEqual(timeline.band_kind(_at_hour(23)), 'night')

    def test_band_kind_falsy_timestamp_is_earlier(self):
        self.assertEqual(timeline.band_kind(0), 'earlier')
        self.assertEqual(timeline.band_kind(None), 'earlier')


# --- day_label ---
#
# Expected strings are derived the same way timeline.day_label itself
# builds them (gettext for Today/Yesterday, time.strftime for the rest)
# rather than hardcoded English, so these don't depend on the LC_TIME
# locale or on gettext translations being bound in the process.

def _weekday_only(day_ymd):
    epoch = time.mktime(day_ymd + (12, 0, 0, 0, 0, -1))
    return time.strftime('%A', time.localtime(epoch))


def _full_date(day_ymd, with_year):
    epoch = time.mktime(day_ymd + (12, 0, 0, 0, 0, -1))
    when = time.localtime(epoch)
    if with_year:
        return '%s, %d %s %d' % (time.strftime('%A', when), when.tm_mday,
                                 time.strftime('%B', when), when.tm_year)
    return '%s, %d %s' % (time.strftime('%A', when), when.tm_mday,
                          time.strftime('%B', when))


class DayLabelTest(unittest.TestCase):

    def test_day_label_today(self):
        now = time.mktime((2026, 8, 15, 12, 0, 0, 0, 0, -1))
        self.assertEqual(
            timeline.day_label((2026, 8, 15), now), timeline._('Today'))

    def test_day_label_yesterday(self):
        now = time.mktime((2026, 8, 15, 12, 0, 0, 0, 0, -1))
        self.assertEqual(
            timeline.day_label((2026, 8, 14), now), timeline._('Yesterday'))

    def test_day_label_recent_weekday_name(self):
        now = time.mktime((2026, 8, 15, 12, 0, 0, 0, 0, -1))
        # 2026-08-12 is 3 days back -- inside the bare-weekday window.
        day = (2026, 8, 12)
        self.assertEqual(timeline.day_label(day, now), _weekday_only(day))

    def test_day_label_weekday_boundary_at_six_days(self):
        now = time.mktime((2026, 8, 15, 12, 0, 0, 0, 0, -1))
        # 6 days back -- still inside the bare-weekday window (<= 6).
        day = (2026, 8, 9)
        self.assertEqual(timeline.day_label(day, now), _weekday_only(day))

    def test_day_label_full_date_boundary_at_seven_days(self):
        now = time.mktime((2026, 8, 15, 12, 0, 0, 0, 0, -1))
        # 7 days back -- just past the bare-weekday window (<= 6).
        day = (2026, 8, 8)
        self.assertEqual(
            timeline.day_label(day, now), _full_date(day, with_year=False))

    def test_day_label_full_date_same_year(self):
        now = time.mktime((2026, 8, 15, 12, 0, 0, 0, 0, -1))
        # 10 days back, same year -- past the weekday-only window (<= 6).
        day = (2026, 8, 5)
        self.assertEqual(
            timeline.day_label(day, now), _full_date(day, with_year=False))

    def test_day_label_full_date_with_year_when_year_differs(self):
        now = time.mktime((2026, 8, 15, 12, 0, 0, 0, 0, -1))
        day = (2025, 7, 11)
        self.assertEqual(
            timeline.day_label(day, now), _full_date(day, with_year=True))

    def test_day_label_future_timestamp_gets_a_full_date(self):
        # A clock-skewed future date must not pass as a nearby weekday.
        now = time.mktime((2026, 8, 15, 12, 0, 0, 0, 0, -1))
        tomorrow = time.localtime(now + 86400)[:3]
        far_future = time.localtime(now + 400 * 86400)[:3]
        self.assertEqual(timeline.day_label(tomorrow, now), _full_date(
            tomorrow, with_year=False))
        self.assertEqual(timeline.day_label(far_future, now), _full_date(
            far_future, with_year=True))


# --- is_date_sort / sort_field ---

class IsDateSortSortFieldTest(unittest.TestCase):

    def test_is_date_sort_defaults_true_when_unset(self):
        self.assertTrue(timeline.is_date_sort(None))
        self.assertTrue(timeline.is_date_sort([]))

    def test_is_date_sort_true_for_timestamp_and_creation_time(self):
        self.assertTrue(timeline.is_date_sort(['-timestamp']))
        self.assertTrue(timeline.is_date_sort(['+creation_time']))

    def test_is_date_sort_false_for_other_fields(self):
        self.assertFalse(timeline.is_date_sort(['-filesize']))

    def test_sort_field_defaults_to_timestamp(self):
        self.assertEqual(timeline.sort_field(None), 'timestamp')
        self.assertEqual(timeline.sort_field(['-timestamp']), 'timestamp')
        self.assertEqual(timeline.sort_field(['-filesize']), 'timestamp')

    def test_sort_field_creation_time(self):
        self.assertEqual(
            timeline.sort_field(['-creation_time']), 'creation_time')
        self.assertEqual(
            timeline.sort_field(['+creation_time']), 'creation_time')


# --- hex color helpers ---

class HexColorHelpersTest(unittest.TestCase):

    def test_hex_to_rgb_with_and_without_hash(self):
        self.assertEqual(timeline.hex_to_rgb('#FF0080'), (255, 0, 128))
        self.assertEqual(timeline.hex_to_rgb('FF0080'), (255, 0, 128))

    def test_hex_to_rgb01_normalizes_to_unit_range(self):
        self.assertEqual(timeline.hex_to_rgb01('#FFFFFF'), (1.0, 1.0, 1.0))
        self.assertEqual(timeline.hex_to_rgb01('#000000'), (0.0, 0.0, 0.0))


# --- rounded_rect_path geometry (ImageSurface, no display needed) ---

class RoundedRectPathTest(unittest.TestCase):

    def test_rounded_rect_path_bounding_box(self):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 100, 100)
        cr = cairo.Context(surface)
        timeline.rounded_rect_path(cr, 10, 10, 40, 20, 5)
        x0, y0, x1, y1 = cr.path_extents()
        _assert_bbox_approx((x0, y0, x1, y1), (10, 10, 50, 30))

    def test_rounded_rect_path_clamps_radius_to_half_extent(self):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 100, 100)
        cr = cairo.Context(surface)
        # radius far larger than either half-dimension must clamp rather
        # than distort or overflow the requested rectangle.
        timeline.rounded_rect_path(cr, 0, 0, 10, 20, 999)
        x0, y0, x1, y1 = cr.path_extents()
        _assert_bbox_approx((x0, y0, x1, y1), (0, 0, 10, 20))


if __name__ == '__main__':
    unittest.main()
