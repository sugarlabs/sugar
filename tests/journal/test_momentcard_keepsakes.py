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

# gi is an apt-installed system package, not something `uvx pytest`'s
# own managed interpreter has -- skip rather than error when it isn't
# importable.
#
# Gtk/Gdk must be pinned to 3.0 before jarabe.journal.momentcard pulls
# them in bare (via jarabe.journal.model), or PyGObject resolves Gdk to
# 4.0 first and the later Gtk 3.0 import conflicts with it.
try:
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
except (ImportError, ValueError):
    raise unittest.SkipTest('gi is not available')

# jarabe isn't on sys.path outside a built/installed tree.
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from jarabe.journal import momentcard  # noqa: E402


# --- _add_moment: the moment record and its cap, owned by momentcard
# itself. The shell-memory guarding of a written moment now lives in
# reflectguard.ReflectionsGuard; see test_reflectguard.py. ---

class TestAddMoment(unittest.TestCase):

    def test_add_moment_appends_a_moment_with_no_eviction_under_the_cap(
            self):
        data = {}
        moment, evicted = momentcard._add_moment(
            data, 'a dragon wing', 'proud')

        self.assertEqual(evicted, [])
        self.assertEqual(data['moments'], [moment])
        self.assertEqual(moment['caption'], 'a dragon wing')
        self.assertEqual(moment['mark'], 'proud')
        self.assertEqual(moment['snap_seq'], 0)
        self.assertEqual(data['moment_seq'], 1)

    def test_add_moment_evicts_the_oldest_past_the_cap(self):
        data = {}
        last_evicted = None
        for i in range(momentcard._MAX_MOMENTS + 1):
            _moment, last_evicted = momentcard._add_moment(
                data, 'caption-%d' % i, 'proud')

        # the call that crossed the cap evicted snap_seq 0, the oldest
        self.assertEqual(last_evicted, [0])
        self.assertEqual(len(data['moments']), momentcard._MAX_MOMENTS)
        self.assertEqual(
            [m['snap_seq'] for m in data['moments']],
            list(range(1, momentcard._MAX_MOMENTS + 1)))


if __name__ == '__main__':
    unittest.main()
