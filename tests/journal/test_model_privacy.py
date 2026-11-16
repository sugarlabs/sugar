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
import tempfile
import unittest

# gi is an apt-installed system package, not something `uvx pytest`'s
# own managed interpreter has -- skip rather than error when it isn't
# importable. Gtk/Gdk must be pinned to 3.0 before jarabe.journal.model
# pulls them in bare.
try:
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
except (ImportError, ValueError):
    raise unittest.SkipTest('gi is not available')

# jarabe isn't on sys.path outside a built/installed tree.
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from jarabe.journal import model  # noqa: E402


class TestRewritesEntryInPlace(unittest.TestCase):
    """The one gate that decides whether a child's talk with Jo rides
    along with an entry. False here means strip; anything that is not
    provably the entry rewriting itself on its own volume must strip.
    """

    def setUp(self):
        self.volume = tempfile.mkdtemp()
        self.addCleanup(_rmtree, self.volume)
        self.entry = os.path.join(self.volume, 'drawing.png')
        open(self.entry, 'w').close()

    def test_rewrite_on_its_own_volume_keeps_the_talk(self):
        self.assertTrue(model._rewrites_entry_in_place(
            {'uid': self.entry, 'mountpoint': self.volume}))

    def test_trailing_slash_on_the_mountpoint_still_matches(self):
        self.assertTrue(model._rewrites_entry_in_place(
            {'uid': self.entry, 'mountpoint': self.volume + '/'}))

    def test_copy_out_of_the_datastore_strips(self):
        # A datastore entry has no file path of its own to rewrite.
        self.assertFalse(model._rewrites_entry_in_place(
            {'mountpoint': self.volume}))

    def test_a_datastore_object_id_is_not_a_path(self):
        self.assertFalse(model._rewrites_entry_in_place(
            {'uid': '6f1a2b3c-4d5e-6f70-8192-a3b4c5d6e7f8',
             'mountpoint': self.volume}))

    def test_copy_between_volumes_strips(self):
        other = tempfile.mkdtemp()
        self.addCleanup(_rmtree, other)
        self.assertFalse(model._rewrites_entry_in_place(
            {'uid': self.entry, 'mountpoint': other}))

    def test_a_sibling_volume_sharing_a_name_prefix_strips(self):
        # /media/stick must not look like a rewrite of /media/stick2.
        sibling = self.volume + '2'
        os.makedirs(sibling)
        self.addCleanup(_rmtree, sibling)
        stray = os.path.join(sibling, 'drawing.png')
        open(stray, 'w').close()
        self.assertFalse(model._rewrites_entry_in_place(
            {'uid': stray, 'mountpoint': self.volume}))

    def test_a_path_that_no_longer_exists_strips(self):
        os.unlink(self.entry)
        self.assertFalse(model._rewrites_entry_in_place(
            {'uid': self.entry, 'mountpoint': self.volume}))

    def test_a_missing_uid_never_reaches_the_mountpoint(self):
        # Short-circuit order matters: callers reach this gate having
        # already indexed 'mountpoint', but 'uid' may legitimately be
        # absent, and testing it first is what keeps that safe.
        self.assertFalse(model._rewrites_entry_in_place({}))


def _rmtree(path):
    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            os.unlink(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(path)


if __name__ == '__main__':
    unittest.main()
