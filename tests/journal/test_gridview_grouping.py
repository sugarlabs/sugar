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

# gi is an apt-installed system package, not something `uvx pytest`'s
# own managed interpreter has -- skip rather than error when it isn't
# importable.
try:
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
except (ImportError, ValueError):
    raise unittest.SkipTest('gi is not available')

# jarabe isn't on sys.path outside a built/installed tree.
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from jarabe.journal import gridview  # noqa: E402


def _at(hour, minute=0):
    return time.mktime((2026, 8, 15, hour, minute, 0, 0, 0, -1))


def _entry(uid, hour, minute=0, activity='org.laptop.Foo'):
    return {'uid': uid, 'timestamp': _at(hour, minute), 'activity': activity}


# --- the suspected single-first-ever-entry [-1] IndexError path ---
#
# CURRENT BEHAVIOR: none of _group_into_bands, _split_into_sittings, or
# _group_sittings raise IndexError on a single entry or an empty list.
# Each list-building loop appends a fresh bucket (bands.append([]) /
# sittings.append([])) before the first bands[-1] / sittings[-1] access,
# and that append is unconditional on the first entry because
# `previous_kind`/`previous_run` starts as None, which never equals a
# real band kind or run tuple. No crash reproduces here -- recorded as
# a confirmed absence, not assumed.

class TestSingleAndEmptyEntryDoesNotCrash(unittest.TestCase):

    def test_group_into_bands_single_first_ever_entry_does_not_crash(self):
        entries = [_entry('only', 10)]
        bands = gridview._group_into_bands(entries, 'timestamp')
        self.assertEqual(bands, [('morning', entries)])

    def test_group_into_bands_empty_list_does_not_crash(self):
        self.assertEqual(gridview._group_into_bands([], 'timestamp'), [])

    def test_split_into_sittings_single_first_ever_entry_does_not_crash(
            self):
        entries = [_entry('only', 10)]
        self.assertEqual(
            gridview._split_into_sittings(entries, 'timestamp'), [entries])

    def test_split_into_sittings_empty_list_does_not_crash(self):
        self.assertEqual(gridview._split_into_sittings([], 'timestamp'), [])

    def test_group_sittings_single_first_ever_entry_does_not_crash(self):
        entries = [_entry('only', 10)]
        trays, loose = gridview._group_sittings(entries, 'timestamp')
        self.assertEqual(trays, {})
        self.assertEqual(loose, {'only'})

    def test_group_sittings_empty_list_does_not_crash(self):
        trays, loose = gridview._group_sittings([], 'timestamp')
        self.assertEqual(trays, {})
        self.assertEqual(loose, set())


# --- multiple entries, same sitting ---

class TestGroupSittings(unittest.TestCase):

    def test_group_sittings_trays_consecutive_same_activity_same_band(self):
        entries = [
            _entry('a', 10, 0), _entry('b', 10, 5), _entry('c', 10, 10)]
        trays, loose = gridview._group_sittings(entries, 'timestamp')
        self.assertEqual(list(trays.keys()), ['a'])
        self.assertEqual([e['uid'] for e in trays['a']], ['a', 'b', 'c'])
        self.assertEqual(loose, set())

    def test_group_sittings_different_activity_breaks_the_sitting(self):
        entries = [
            _entry('a', 10, 0, activity='org.laptop.Foo'),
            _entry('b', 10, 5, activity='org.laptop.Bar'),
            _entry('c', 10, 10, activity='org.laptop.Foo'),
        ]
        trays, loose = gridview._group_sittings(entries, 'timestamp')
        self.assertEqual(trays, {})
        self.assertEqual(loose, {'a', 'b', 'c'})

    def test_group_sittings_band_change_breaks_the_sitting(self):
        entries = [
            _entry('a', 11, 55, activity='org.laptop.Foo'),
            _entry('b', 12, 5, activity='org.laptop.Foo'),
        ]
        trays, loose = gridview._group_sittings(entries, 'timestamp')
        self.assertEqual(trays, {})
        self.assertEqual(loose, {'a', 'b'})

    def test_group_sittings_day_change_breaks_the_sitting(self):
        entries = [
            {'uid': 'a', 'timestamp': _at(23, 0),
             'activity': 'org.laptop.Foo'},
            {'uid': 'b',
             'timestamp': time.mktime((2026, 8, 16, 0, 30, 0, 0, 0, -1)),
             'activity': 'org.laptop.Foo'},
        ]
        trays, loose = gridview._group_sittings(entries, 'timestamp')
        self.assertEqual(trays, {})
        self.assertEqual(loose, {'a', 'b'})

    def test_group_sittings_never_trays_entries_without_activity(self):
        # loose_uids is built from the full entries list, not the
        # activity-filtered datable() list, so an entry with no activity
        # is never trayed -- it stays loose (shown as its own card).
        entries = [
            _entry('a', 10, 0, activity=''),
            _entry('b', 10, 5, activity=''),
        ]
        trays, loose = gridview._group_sittings(entries, 'timestamp')
        self.assertEqual(trays, {})
        self.assertEqual(loose, {'a', 'b'})


# --- band boundaries ---

class TestGroupIntoBandsBoundaries(unittest.TestCase):

    def test_group_into_bands_splits_on_boundary(self):
        entries = [
            _entry('a', 11, 0), _entry('b', 11, 30), _entry('c', 13, 0)]
        bands = gridview._group_into_bands(entries, 'timestamp')
        self.assertEqual(
            [kind for kind, _items in bands], ['morning', 'afternoon'])
        self.assertEqual([e['uid'] for e in bands[0][1]], ['a', 'b'])
        self.assertEqual([e['uid'] for e in bands[1][1]], ['c'])

    def test_group_into_bands_keeps_same_kind_entries_in_one_bucket(self):
        entries = [_entry('a', 6), _entry('b', 7), _entry('c', 8)]
        bands = gridview._group_into_bands(entries, 'timestamp')
        self.assertEqual(len(bands), 1)
        self.assertEqual(bands[0][0], 'morning')

    def test_group_into_bands_reopens_a_new_bucket_when_the_kind_returns(
            self):
        # CURRENT BEHAVIOR: grouping is by consecutive run only, so
        # out-of-order input re-opens a same-kind bucket rather than
        # merging it with an earlier one of the same kind.
        entries = [_entry('a', 11), _entry('b', 13), _entry('c', 11, 30)]
        bands = gridview._group_into_bands(entries, 'timestamp')
        self.assertEqual(
            [kind for kind, _items in bands],
            ['morning', 'afternoon', 'morning'])


# --- _datable / _entry_date / _caption_field / _entry_filesize ---

class TestDatableAndFieldHelpers(unittest.TestCase):

    def test_datable_requires_activity_and_a_real_date(self):
        entries = [
            _entry('has-both', 10),
            {'uid': 'no-activity', 'timestamp': _at(10), 'activity': ''},
            {'uid': 'no-timestamp', 'timestamp': 0,
             'activity': 'org.laptop.Foo'},
        ]
        datable = gridview._datable(entries, 'timestamp')
        self.assertEqual([e['uid'] for e in datable], ['has-both'])

    def test_entry_date_creation_time_falls_back_to_timestamp(self):
        metadata = {'timestamp': 1000}
        self.assertEqual(
            gridview._entry_date(metadata, 'creation_time'), 1000.0)

    def test_entry_date_creation_time_present(self):
        metadata = {'timestamp': 1000, 'creation_time': 2000}
        self.assertEqual(
            gridview._entry_date(metadata, 'creation_time'), 2000.0)

    def test_caption_field_mirrors_date_sort(self):
        self.assertEqual(gridview._caption_field(['-timestamp']), 'timestamp')
        self.assertEqual(
            gridview._caption_field(['-creation_time']), 'creation_time')
        self.assertEqual(gridview._caption_field(['-filesize']), 'filesize')

    def test_entry_filesize_guards_nan_and_missing(self):
        self.assertIsNone(gridview._entry_filesize({'filesize': 'nan'}))
        self.assertIsNone(gridview._entry_filesize({}))
        self.assertEqual(gridview._entry_filesize({'filesize': '2048'}), 2048)

    def test_format_clock_time_zero_is_blank(self):
        self.assertEqual(gridview._format_clock_time(0), '')

    def test_card_render_key_tracks_render_relevant_fields(self):
        metadata = {'uid': 'u', 'title': 't', 'timestamp': 1, 'filesize': 2}
        key = gridview._card_render_key(metadata, 3, 'timestamp')
        self.assertEqual(
            key,
            ('u', 't', 1, None, 2, None, None, None, None, None, 3,
             'timestamp'))


if __name__ == '__main__':
    unittest.main()
