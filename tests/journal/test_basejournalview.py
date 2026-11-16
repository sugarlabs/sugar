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

    # Gtk/Gdk must be pinned to 3.0 before jarabe.journal.basejournalview
    # pulls them in bare, or PyGObject resolves Gdk to 4.0 first and the
    # later Gtk 3.0 import conflicts with it.
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
except (ImportError, ValueError):
    raise unittest.SkipTest('gi is not available')

# jarabe isn't on sys.path outside a built/installed tree.
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from jarabe.journal.basejournalview import BaseJournalView  # noqa: E402


class _RecordingModel:

    def __init__(self):
        self.restored = None

    def restore_selection(self, selected):
        self.restored = selected


class _View(BaseJournalView):
    # A real Gtk.Bin is fine to instantiate without a display; only
    # realizing/showing one on screen needs one, and this test never
    # does. _repaint_selection is abstract on the base (NotImplementedError)
    # so the minimal subclass just has to give it a body.

    def __init__(self):
        BaseJournalView.__init__(self)
        self.repaint_calls = 0

    def _repaint_selection(self):
        self.repaint_calls += 1


# --- carry_selection ---

class CarrySelectionTest(unittest.TestCase):

    def setUp(self):
        self.view = _View()

    def test_carry_selection_dirty_stores_and_skips_repaint(self):
        view = self.view
        view._dirty = True
        view._model_ready = True
        view.carry_selection({'a', 'b'})
        self.assertEqual(view._carried_selected, {'a', 'b'})
        self.assertEqual(view.repaint_calls, 0)

    def test_carry_selection_not_ready_stores_and_skips_repaint(self):
        view = self.view
        view._dirty = False
        view._model_ready = False
        view.carry_selection({'a'})
        self.assertEqual(view._carried_selected, {'a'})
        self.assertEqual(view.repaint_calls, 0)

    def test_carry_selection_ready_and_clean_repaints_immediately(self):
        view = self.view
        view._dirty = False
        view._model_ready = True
        view.carry_selection({'a'})
        self.assertEqual(view.repaint_calls, 1)
        self.assertIsNone(view._carried_selected)

    def test_carry_selection_restores_selection_on_the_model_when_present(
            self):
        view = self.view
        model_stub = _RecordingModel()
        view._model = model_stub
        view._dirty = False
        view._model_ready = True
        view.carry_selection({'x', 'y'})
        self.assertEqual(sorted(model_stub.restored), ['x', 'y'])

    def test_carry_selection_skips_restore_when_model_is_none(self):
        view = self.view
        self.assertIsNone(view._model)
        view._dirty = False
        view._model_ready = False
        view.carry_selection({'z'})  # must not touch a model that isn't there
        self.assertEqual(view._carried_selected, {'z'})

    def test_carry_selection_restores_before_checking_dirty_flags(self):
        # restore_selection runs whether or not the carry gets deferred --
        # it feeds the model's own selection bookkeeping either way.
        view = self.view
        model_stub = _RecordingModel()
        view._model = model_stub
        view._dirty = True
        view.carry_selection({'p'})
        self.assertEqual(model_stub.restored, ['p'])
        self.assertEqual(view._carried_selected, {'p'})


# --- _defer_refresh ---

class DeferRefreshTest(unittest.TestCase):

    def setUp(self):
        self.view = _View()

    def test_defer_refresh_obscured_marks_dirty_and_returns_true(self):
        view = self.view
        view._fully_obscured = True
        view._dirty = False
        view._dirty_new_query = False
        self.assertIs(view._defer_refresh(True), True)
        self.assertIs(view._dirty, True)
        self.assertIs(view._dirty_new_query, True)

    def test_defer_refresh_obscured_without_new_query_keeps_it_false(
            self):
        view = self.view
        view._fully_obscured = True
        view._dirty_new_query = False
        self.assertIs(view._defer_refresh(False), True)
        self.assertIs(view._dirty_new_query, False)

    def test_defer_refresh_obscured_never_clears_a_pending_new_query(
            self):
        view = self.view
        view._fully_obscured = True
        view._dirty_new_query = True
        self.assertIs(view._defer_refresh(False), True)
        self.assertIs(view._dirty_new_query, True)

    def test_defer_refresh_visible_returns_false_and_leaves_state_alone(
            self):
        view = self.view
        view._fully_obscured = False
        view._dirty = False
        view._dirty_new_query = False
        self.assertIs(view._defer_refresh(True), False)
        self.assertIs(view._dirty, False)
        self.assertIs(view._dirty_new_query, False)


# --- _is_new_item_visible ---

class IsNewItemVisibleTest(unittest.TestCase):

    def setUp(self):
        self.view = _View()

    def test_is_new_item_visible_no_mountpoints_key_returns_none(self):
        view = self.view
        view._query = {}
        self.assertIsNone(view._is_new_item_visible('/foo'))

    def test_is_new_item_visible_empty_mountpoints_returns_none(self):
        view = self.view
        view._query = {'mountpoints': []}
        self.assertIsNone(view._is_new_item_visible('/foo'))

    def test_is_new_item_visible_root_mountpoint(self):
        view = self.view
        view._query = {'mountpoints': ['/']}
        self.assertIs(view._is_new_item_visible('/media/usb/x'), False)
        self.assertIs(view._is_new_item_visible('some-datastore-uid'), True)

    def test_is_new_item_visible_specific_mountpoint(self):
        view = self.view
        view._query = {'mountpoints': ['/media/usb']}
        self.assertIs(view._is_new_item_visible('/media/usb/x'), True)
        self.assertIs(view._is_new_item_visible('/media/other'), False)


# --- get_projects_view_active ---

class GetProjectsViewActiveTest(unittest.TestCase):

    def setUp(self):
        self.view = _View()

    def test_get_projects_view_active_defaults_false(self):
        view = self.view
        self.assertIs(view.get_projects_view_active(), False)


if __name__ == '__main__':
    unittest.main()
