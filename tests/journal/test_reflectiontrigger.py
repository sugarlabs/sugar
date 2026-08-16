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
import unittest

try:
    # gi is an apt-installed system package, not something `uvx pytest`'s
    # own managed interpreter has -- skip rather than error when it isn't
    # importable.
    import gi

    # Gtk/Gdk must be pinned to 3.0 before jarabe.journal.reflectiontrigger
    # pulls them in bare, or PyGObject resolves Gtk to 4.0 first and the
    # later 3.0 imports conflict with it.
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
    gi.require_version('SugarExt', '1.0')
except (ImportError, ValueError):
    raise unittest.SkipTest('gi is not available')

# jarabe isn't on sys.path outside a built/installed tree.
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from jarabe.journal.reflectiontrigger import earned_invite  # noqa: E402
from jarabe.journal.reflectiontrigger import FIND_PROPERTIES  # noqa: E402
from jarabe.journal.reflectiontrigger import MIN_ACTIVE_SECONDS  # noqa: E402


def _entry(filesize='1024', spent='%d' % MIN_ACTIVE_SECONDS):
    return {'filesize': filesize, 'spent-times': spent}


class TestEarnedInvite(unittest.TestCase):

    # --- the two gates: a payload and a real stretch of focus ---

    def test_real_work_earns_the_note(self):
        self.assertTrue(earned_invite(_entry()))

    def test_no_metadata_at_all_stays_silent(self):
        self.assertFalse(earned_invite({}))

    def test_missing_file_stays_silent(self):
        self.assertFalse(earned_invite({'spent-times': '300'}))

    def test_empty_file_stays_silent(self):
        self.assertFalse(earned_invite(_entry(filesize='0')))

    def test_garbage_filesize_stays_silent(self):
        self.assertFalse(earned_invite(_entry(filesize='huge')))

    def test_nan_filesize_stays_silent(self):
        self.assertFalse(earned_invite(_entry(filesize='nan')))

    def test_inf_filesize_stays_silent(self):
        self.assertFalse(earned_invite(_entry(filesize='inf')))

    def test_integer_filesize_from_datastore_counts(self):
        self.assertTrue(earned_invite(_entry(filesize=2048)))

    def test_integer_spent_times_parses_too(self):
        self.assertTrue(earned_invite(_entry(spent=MIN_ACTIVE_SECONDS)))

    def test_missing_spent_times_stays_silent(self):
        self.assertFalse(earned_invite({'filesize': '1024'}))

    def test_a_peek_below_the_bar_stays_silent(self):
        self.assertFalse(earned_invite(
            _entry(spent='%d' % (MIN_ACTIVE_SECONDS - 1))))

    def test_the_bar_itself_earns_the_note(self):
        self.assertTrue(earned_invite(_entry(spent='%d' % MIN_ACTIVE_SECONDS)))

    def test_only_the_last_session_counts(self):
        # the toolkit appends this session's seconds as the last value
        self.assertTrue(earned_invite(_entry(spent='3, 900')))
        self.assertFalse(earned_invite(_entry(spent='900, 3')))

    def test_toolkit_comma_space_join_parses(self):
        self.assertTrue(earned_invite(_entry(spent='12, 45, 300')))

    def test_bare_comma_join_parses_too(self):
        self.assertTrue(earned_invite(_entry(spent='12,300')))

    def test_garbage_spent_times_stays_silent(self):
        self.assertFalse(earned_invite(_entry(spent='yesterday')))

    def test_trailing_separator_stays_silent(self):
        self.assertFalse(earned_invite(_entry(spent='300, ')))

    def test_the_query_requests_what_the_gate_reads(self):
        # dropping either key from the find() would disable the note
        # for every activity, silently
        self.assertIn('filesize', FIND_PROPERTIES)
        self.assertIn('spent-times', FIND_PROPERTIES)


if __name__ == '__main__':
    unittest.main()
