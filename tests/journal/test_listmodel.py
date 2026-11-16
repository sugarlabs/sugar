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

import logging
import os
import sys
import unittest
from gettext import gettext as _
from types import SimpleNamespace
from unittest import mock

try:
    # gi is an apt-installed system package, not something `uvx pytest`'s
    # own managed interpreter has -- skip rather than error when it isn't
    # importable.
    import gi

    # Gtk/Gdk must be pinned to 3.0 before jarabe.journal.listmodel pulls
    # them in bare, or PyGObject resolves Gdk to 4.0 first and the later
    # Gtk 3.0 import conflicts with it.
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
except (ImportError, ValueError):
    raise unittest.SkipTest('gi is not available')

# jarabe isn't on sys.path outside a built/installed tree.
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from jarabe.journal import listmodel  # noqa: E402
from jarabe.journal import misc  # noqa: E402
from jarabe.journal import model  # noqa: E402


class _Signal:
    """Stand-in for the ready/progress dispatch.Signal a real
    ResultSet carries -- ListModel.__init__ only needs .connect() to
    exist on it, it never has to actually fire in these tests."""

    def connect(self, callback):
        pass


class _FakeResultSet:

    def __init__(self, entries):
        self.entries = entries
        self.length = len(entries)
        self.position = None
        self.seek_calls = []
        self.ready = _Signal()
        self.progress = _Signal()

    def seek(self, index):
        self.seek_calls.append(index)
        self.position = index

    def read(self):
        return dict(self.entries[self.position])

    def find_ids(self, query):
        return [entry['uid'] for entry in self.entries]

    def setup(self):
        pass

    def stop(self):
        pass


def _make_model(monkeypatch, entries):
    fake_rs = _FakeResultSet(entries)
    monkeypatch.setattr(model, 'find', lambda query, page_size: fake_rs)
    return listmodel.ListModel({}), fake_rs


def _iter_at(index):
    return SimpleNamespace(user_data=index)


class _MonkeyPatch:
    """Minimal replacement for pytest's monkeypatch fixture: same
    .setattr(target, name, value) interface, but cleaned up through
    the owning TestCase's addCleanup instead of fixture teardown."""

    def __init__(self, testcase):
        self._patchers = []
        testcase.addCleanup(self._undo)

    def setattr(self, target, name, value):
        patcher = mock.patch.object(target, name, value)
        patcher.start()
        self._patchers.append(patcher)

    def _undo(self):
        for patcher in reversed(self._patchers):
            patcher.stop()


def stub_misc(monkeypatch):
    # get_icon_name/is_activity_bundle/get_icon_color reach into
    # bundleregistry and the datastore -- stub them at the misc
    # boundary so do_get_value's own branching is what's under test.
    monkeypatch.setattr(misc, 'get_icon_name', lambda metadata: 'icon-name')
    monkeypatch.setattr(misc, 'is_activity_bundle', lambda metadata: False)
    monkeypatch.setattr(
        misc, 'get_icon_color', lambda metadata: 'icon-color-sentinel')


def stub_elapsed(monkeypatch):
    # timestamp_to_elapsed_string keys its i18n cache off
    # os.environ['LANG'] -- stub it so timestamp columns are
    # deterministic without depending on the runner's locale.
    monkeypatch.setattr(
        listmodel.util, 'timestamp_to_elapsed_string',
        lambda ts: 'elapsed:%s' % ts)


# --- _remember_row_facts: timestamp/creation_time fallbacks, sitting key ---

class RememberRowFactsTest(unittest.TestCase):

    def test_remember_row_facts_missing_timestamp_defaults_to_zero(self):
        monkeypatch = _MonkeyPatch(self)
        lm, _rs = _make_model(monkeypatch, [])
        facts = lm._remember_row_facts(
            0, {'uid': 'a', 'activity': 'org.laptop.Foo'})
        self.assertEqual(facts, ('a', 0.0, 'org.laptop.Foo', 0.0))

    def test_remember_row_facts_missing_creation_time_reuses_timestamp(
            self):
        monkeypatch = _MonkeyPatch(self)
        lm, _rs = _make_model(monkeypatch, [])
        facts = lm._remember_row_facts(
            0, {'uid': 'a', 'timestamp': 1000, 'activity': 'org.laptop.Foo'})
        self.assertEqual(facts[1], 1000.0)
        self.assertEqual(facts[3], 1000.0)

    def test_remember_row_facts_invalid_creation_time_falls_back_to_parsed_ts(  # noqa: E501
            self):
        monkeypatch = _MonkeyPatch(self)
        lm, _rs = _make_model(monkeypatch, [])
        facts = lm._remember_row_facts(
            0, {'uid': 'a', 'timestamp': 1000, 'creation_time': 'garbage',
                'activity': 'org.laptop.Foo'})
        # safe_timestamp's `default` for creation_time is the already-parsed
        # timestamp fact (1000.0), not the raw metadata value -- an
        # unparseable creation_time reuses the derived fact rather than
        # re-deriving anything from scratch.
        self.assertEqual(facts[3], 1000.0)

    def test_remember_row_facts_valid_creation_time_is_used_verbatim(
            self):
        monkeypatch = _MonkeyPatch(self)
        lm, _rs = _make_model(monkeypatch, [])
        facts = lm._remember_row_facts(
            0, {'uid': 'a', 'timestamp': 1000, 'creation_time': 2000,
                'activity': 'org.laptop.Foo'})
        self.assertEqual(facts[3], 2000.0)

    def test_remember_row_facts_sitting_key_prefers_activity_over_icon_lookup(  # noqa: E501
            self):
        monkeypatch = _MonkeyPatch(self)
        lm, _rs = _make_model(monkeypatch, [])

        def boom(metadata):
            raise AssertionError('get_icon_name ran despite activity present')
        monkeypatch.setattr(misc, 'get_icon_name', boom)

        facts = lm._remember_row_facts(
            0, {'uid': 'a', 'activity': 'org.laptop.Foo'})
        self.assertEqual(facts[2], 'org.laptop.Foo')

    def test_remember_row_facts_sitting_key_falls_back_to_icon_name(
            self):
        monkeypatch = _MonkeyPatch(self)
        stub_misc(monkeypatch)
        lm, _rs = _make_model(monkeypatch, [])
        facts = lm._remember_row_facts(0, {'uid': 'a'})
        self.assertEqual(facts[2], 'icon-name')

    def test_remember_row_facts_stores_into_the_row_facts_cache(self):
        monkeypatch = _MonkeyPatch(self)
        lm, _rs = _make_model(monkeypatch, [])
        facts = lm._remember_row_facts(3, {'uid': 'a', 'activity': 'x'})
        self.assertEqual(lm._row_facts[3], facts)


# --- get_row_facts: cache short-circuit, guards, updated-entry merge ---

class GetRowFactsTest(unittest.TestCase):

    def test_get_row_facts_returns_none_when_view_is_resizing(self):
        monkeypatch = _MonkeyPatch(self)
        lm, _rs = _make_model(monkeypatch, [{'uid': 'a', 'activity': 'x'}])
        lm.view_is_resizing = True
        self.assertIsNone(lm.get_row_facts(0))

    def test_get_row_facts_returns_none_for_out_of_range_index(self):
        monkeypatch = _MonkeyPatch(self)
        lm, _rs = _make_model(monkeypatch, [{'uid': 'a', 'activity': 'x'}])
        self.assertIsNone(lm.get_row_facts(1))

    def test_get_row_facts_reads_through_and_caches(self):
        monkeypatch = _MonkeyPatch(self)
        lm, rs = _make_model(
            monkeypatch, [{'uid': 'a', 'timestamp': 1000, 'activity': 'x'}])
        facts = lm.get_row_facts(0)
        self.assertEqual(facts, ('a', 1000.0, 'x', 1000.0))
        self.assertEqual(rs.seek_calls, [0])

    def test_get_row_facts_second_call_hits_cache_not_the_result_set(
            self):
        monkeypatch = _MonkeyPatch(self)
        lm, rs = _make_model(
            monkeypatch, [{'uid': 'a', 'timestamp': 1000, 'activity': 'x'}])
        lm.get_row_facts(0)
        lm.get_row_facts(0)
        self.assertEqual(rs.seek_calls, [0])

    def test_get_row_facts_cache_hit_wins_even_while_view_is_resizing(
            self):
        monkeypatch = _MonkeyPatch(self)
        lm, rs = _make_model(
            monkeypatch, [{'uid': 'a', 'timestamp': 1000, 'activity': 'x'}])
        lm.get_row_facts(0)
        lm.view_is_resizing = True
        seeks_before = list(rs.seek_calls)
        facts = lm.get_row_facts(0)
        self.assertEqual(facts, ('a', 1000.0, 'x', 1000.0))
        self.assertEqual(rs.seek_calls, seeks_before)

    def test_get_row_facts_merges_updated_entries_over_the_stored_read(
            self):
        monkeypatch = _MonkeyPatch(self)
        lm, _rs = _make_model(
            monkeypatch, [{'uid': 'a', 'timestamp': 1000, 'activity': 'x'}])
        lm._updated_entries['a'] = {'timestamp': 5000}
        facts = lm.get_row_facts(0)
        self.assertEqual(facts[1], 5000.0)

    def test_get_row_facts_cache_is_evicted_by_set_value(self):
        monkeypatch = _MonkeyPatch(self)
        stub_misc(monkeypatch)
        # An edit through set_value drops the edited index from the
        # row-facts cache, so the next read re-derives from the merged
        # entry. Direct _updated_entries writes without set_value still
        # leave a populated slot alone (nothing else evicts it).
        lm, _rs = _make_model(
            monkeypatch, [{'uid': 'a', 'timestamp': 1000, 'activity': 'x',
                           'title': 'old'}])
        lm.setup(updated_callback=None)
        monkeypatch.setattr(model, 'write', lambda *a, **kw: None)
        lm.get_row_facts(0)
        lm.set_value(_iter_at(0), listmodel.ListModel.COLUMN_TITLE, 'new')
        self.assertEqual(lm.get_row_metadata(0)['title'], 'new')


# --- get_row_metadata: same guards, but never touches the facts cache ---

class GetRowMetadataTest(unittest.TestCase):

    def test_get_row_metadata_returns_none_when_view_is_resizing(self):
        monkeypatch = _MonkeyPatch(self)
        lm, _rs = _make_model(monkeypatch, [{'uid': 'a'}])
        lm.view_is_resizing = True
        self.assertIsNone(lm.get_row_metadata(0))

    def test_get_row_metadata_returns_none_for_out_of_range_index(self):
        monkeypatch = _MonkeyPatch(self)
        lm, _rs = _make_model(monkeypatch, [{'uid': 'a'}])
        self.assertIsNone(lm.get_row_metadata(1))

    def test_get_row_metadata_merges_updated_entries(self):
        monkeypatch = _MonkeyPatch(self)
        lm, _rs = _make_model(monkeypatch, [{'uid': 'a', 'title': 'original'}])
        lm._updated_entries['a'] = {'title': 'edited'}
        metadata = lm.get_row_metadata(0)
        self.assertEqual(metadata['title'], 'edited')

    def test_get_row_metadata_returns_a_fresh_copy(self):
        monkeypatch = _MonkeyPatch(self)
        lm, rs = _make_model(monkeypatch, [{'uid': 'a', 'title': 'original'}])
        metadata = lm.get_row_metadata(0)
        metadata['title'] = 'mutated locally'
        self.assertEqual(rs.entries[0]['title'], 'original')

    def test_get_row_metadata_does_not_populate_the_row_facts_cache(
            self):
        monkeypatch = _MonkeyPatch(self)
        lm, _rs = _make_model(monkeypatch, [{'uid': 'a'}])
        lm.get_row_metadata(0)
        self.assertNotIn(0, lm._row_facts)


# --- do_get_value: guarded branches on a mocked result set ---

class DoGetValueTest(unittest.TestCase):

    def test_do_get_value_returns_none_when_view_is_resizing(
            self):
        monkeypatch = _MonkeyPatch(self)
        stub_misc(monkeypatch)
        lm, _rs = _make_model(monkeypatch, [{'uid': 'a', 'activity': 'x'}])
        lm.view_is_resizing = True
        column = listmodel.ListModel.COLUMN_UID
        self.assertIsNone(lm.do_get_value(_iter_at(0), column))

    def test_do_get_value_returns_none_for_out_of_range_index(
            self):
        monkeypatch = _MonkeyPatch(self)
        stub_misc(monkeypatch)
        lm, _rs = _make_model(monkeypatch, [{'uid': 'a', 'activity': 'x'}])
        column = listmodel.ListModel.COLUMN_UID
        self.assertIsNone(lm.do_get_value(_iter_at(5), column))

    def test_do_get_value_title_non_str_guard_falls_back_to_untitled(
            self):
        monkeypatch = _MonkeyPatch(self)
        stub_misc(monkeypatch)
        lm, _rs = _make_model(
            monkeypatch, [{'uid': 'a', 'activity': 'x', 'title': 42}])
        column = listmodel.ListModel.COLUMN_TITLE
        with self.assertLogs(level=logging.WARNING) as cm:
            title = lm.do_get_value(_iter_at(0), column)
        self.assertEqual(title, '<b>%s</b>' % _('Untitled'))
        self.assertIn('is not a string', '\n'.join(cm.output))

    def test_do_get_value_timestamp_falsy_shows_no_date(self):
        monkeypatch = _MonkeyPatch(self)
        stub_misc(monkeypatch)
        lm, _rs = _make_model(monkeypatch, [{'uid': 'a', 'activity': 'x'}])
        column = listmodel.ListModel.COLUMN_TIMESTAMP
        self.assertEqual(lm.do_get_value(_iter_at(0), column), _('No date'))

    def test_do_get_value_timestamp_present_shows_elapsed_string(
            self):
        monkeypatch = _MonkeyPatch(self)
        stub_misc(monkeypatch)
        stub_elapsed(monkeypatch)
        lm, _rs = _make_model(
            monkeypatch,
            [{'uid': 'a', 'activity': 'x', 'timestamp': 1000}])
        column = listmodel.ListModel.COLUMN_TIMESTAMP
        self.assertEqual(
            lm.do_get_value(_iter_at(0), column), 'elapsed:1000.0')

    def test_do_get_value_creation_time_falsy_shows_no_date(
            self):
        monkeypatch = _MonkeyPatch(self)
        stub_misc(monkeypatch)
        lm, _rs = _make_model(monkeypatch, [
            {'uid': 'a', 'activity': 'x', 'timestamp': 0,
             'creation_time': 'garbage'}])
        column = listmodel.ListModel.COLUMN_CREATION_TIME
        self.assertEqual(lm.do_get_value(_iter_at(0), column), _('No date'))

    def test_do_get_value_creation_time_reuses_the_parsed_timestamp_fact(
            self):
        monkeypatch = _MonkeyPatch(self)
        stub_misc(monkeypatch)
        stub_elapsed(monkeypatch)
        lm, _rs = _make_model(
            monkeypatch,
            [{'uid': 'a', 'activity': 'x', 'timestamp': 1000}])
        timestamp_col = lm.do_get_value(
            _iter_at(0), listmodel.ListModel.COLUMN_TIMESTAMP)
        creation_col = lm.do_get_value(
            _iter_at(0), listmodel.ListModel.COLUMN_CREATION_TIME)
        self.assertEqual(timestamp_col, creation_col)
        self.assertEqual(creation_col, 'elapsed:1000.0')

    def test_do_get_value_populates_the_row_facts_cache_as_a_side_effect(
            self):
        monkeypatch = _MonkeyPatch(self)
        stub_misc(monkeypatch)
        lm, _rs = _make_model(
            monkeypatch, [{'uid': 'a', 'activity': 'x', 'timestamp': 1000}])
        lm.do_get_value(_iter_at(0), listmodel.ListModel.COLUMN_UID)
        self.assertEqual(lm._row_facts[0], ('a', 1000.0, 'x', 1000.0))

    def test_do_get_value_reuses_the_last_requested_index_without_reseeking(
            self):
        monkeypatch = _MonkeyPatch(self)
        stub_misc(monkeypatch)
        stub_elapsed(monkeypatch)
        lm, rs = _make_model(
            monkeypatch,
            [{'uid': 'a', 'activity': 'x', 'timestamp': 1000}])
        lm.do_get_value(_iter_at(0), listmodel.ListModel.COLUMN_UID)
        seeks_before = list(rs.seek_calls)
        value = lm.do_get_value(
            _iter_at(0), listmodel.ListModel.COLUMN_TIMESTAMP)
        self.assertEqual(rs.seek_calls, seeks_before)
        self.assertEqual(value, 'elapsed:1000.0')


# --- selection state ---

class SelectionStateTest(unittest.TestCase):

    def test_is_selected_false_for_an_unselected_uid(self):
        monkeypatch = _MonkeyPatch(self)
        lm, _rs = _make_model(monkeypatch, [])
        self.assertIs(lm.is_selected('a'), False)

    def test_set_selected_true_then_is_selected_true(self):
        monkeypatch = _MonkeyPatch(self)
        lm, _rs = _make_model(monkeypatch, [])
        lm.set_selected('a', True)
        self.assertIs(lm.is_selected('a'), True)

    def test_set_selected_false_removes_a_previously_selected_uid(self):
        monkeypatch = _MonkeyPatch(self)
        lm, _rs = _make_model(monkeypatch, [])
        lm.set_selected('a', True)
        lm.set_selected('a', False)
        self.assertIs(lm.is_selected('a'), False)

    def test_set_selected_false_on_a_never_selected_uid_raises(self):
        # CURRENT BEHAVIOR: set_selected(uid, False) calls
        # self._selected.remove(uid) unconditionally -- there is no
        # `if uid in self._selected` guard. Every call site today
        # (listview.py, gridview.py, journaltoolbox.py, palettes.py) only
        # ever deselects a uid it has just confirmed is selected, so this
        # never fires in practice, but the method itself has no internal
        # guard: deselecting (or double-deselecting) a uid that isn't
        # currently selected raises ValueError instead of being a no-op.
        monkeypatch = _MonkeyPatch(self)
        lm, _rs = _make_model(monkeypatch, [])
        with self.assertRaises(ValueError):
            lm.set_selected('never-selected', False)

    def test_get_selected_items_returns_the_live_selection_list(self):
        monkeypatch = _MonkeyPatch(self)
        lm, _rs = _make_model(monkeypatch, [])
        lm.set_selected('a', True)
        lm.set_selected('b', True)
        self.assertEqual(lm.get_selected_items(), ['a', 'b'])

    def test_restore_selection_replaces_the_current_selection(self):
        monkeypatch = _MonkeyPatch(self)
        lm, _rs = _make_model(monkeypatch, [])
        lm.set_selected('a', True)
        lm.restore_selection(['x', 'y'])
        self.assertEqual(lm.get_selected_items(), ['x', 'y'])
        self.assertIs(lm.is_selected('a'), False)


# --- set_value: the updated-signal disconnect/reconnect around write ---

class _RecordingSignal:

    def __init__(self):
        self.calls = []

    def connect(self, callback):
        self.calls.append(('connect', callback))

    def disconnect(self, callback):
        self.calls.append(('disconnect', callback))


def _noop_callback(*args, **kwargs):
    pass


class SetValueTest(unittest.TestCase):

    def test_set_value_favorite_column_updates_keep_and_records_entry(
            self):
        monkeypatch = _MonkeyPatch(self)
        lm, _rs = _make_model(monkeypatch, [{'uid': 'a', 'keep': '0'}])
        lm.setup(updated_callback=None)
        monkeypatch.setattr(model, 'write', lambda *a, **kw: None)
        lm.set_value(_iter_at(0), listmodel.ListModel.COLUMN_FAVORITE, True)
        self.assertIs(lm._updated_entries['a']['keep'], True)

    def test_set_value_title_column_updates_title_and_records_entry(
            self):
        monkeypatch = _MonkeyPatch(self)
        lm, _rs = _make_model(monkeypatch, [{'uid': 'a', 'title': 'old'}])
        lm.setup(updated_callback=None)
        monkeypatch.setattr(model, 'write', lambda *a, **kw: None)
        lm.set_value(_iter_at(0), listmodel.ListModel.COLUMN_TITLE, 'new')
        self.assertEqual(lm._updated_entries['a']['title'], 'new')

    def test_set_value_other_column_still_records_the_entry_unchanged(
            self):
        monkeypatch = _MonkeyPatch(self)
        lm, _rs = _make_model(monkeypatch, [{'uid': 'a', 'title': 'old'}])
        lm.setup(updated_callback=None)
        monkeypatch.setattr(model, 'write', lambda *a, **kw: None)
        lm.set_value(_iter_at(0), listmodel.ListModel.COLUMN_UID, 'ignored')
        self.assertEqual(
            lm._updated_entries['a'], {'uid': 'a', 'title': 'old'})

    def test_set_value_disconnects_before_write_and_reconnects_after(
            self):
        monkeypatch = _MonkeyPatch(self)
        lm, _rs = _make_model(monkeypatch, [{'uid': 'a', 'title': 'old'}])
        lm.setup(updated_callback=_noop_callback)

        recording = _RecordingSignal()
        monkeypatch.setattr(model, 'updated', recording)

        def fake_write(metadata, update_mtime=False, ready_callback=None):
            # the disconnect must already have happened by the time write
            # fires, and the reconnect must not have happened yet.
            self.assertEqual(recording.calls, [('disconnect', _noop_callback)])
            ready_callback(metadata, 'filepath', metadata['uid'])

        monkeypatch.setattr(model, 'write', fake_write)
        lm.set_value(_iter_at(0), listmodel.ListModel.COLUMN_TITLE, 'new')

        self.assertEqual(recording.calls, [
            ('disconnect', _noop_callback), ('connect', _noop_callback)])

    def test_set_value_skips_disconnect_reconnect_without_a_callback(
            self):
        monkeypatch = _MonkeyPatch(self)
        lm, _rs = _make_model(monkeypatch, [{'uid': 'a', 'title': 'old'}])
        lm.setup(updated_callback=None)

        recording = _RecordingSignal()
        monkeypatch.setattr(model, 'updated', recording)
        monkeypatch.setattr(model, 'write', lambda *a, **kw: None)

        lm.set_value(_iter_at(0), listmodel.ListModel.COLUMN_TITLE, 'new')

        self.assertEqual(recording.calls, [])

    def test_set_value_before_setup_raises_attribute_error(self):
        # CURRENT BEHAVIOR: __init__ never initialises _updated_callback --
        # only setup() does -- so set_value on a constructed-but-not-set-up
        # model raises AttributeError instead of cleanly skipping the
        # disconnect the way the `is not None` guard implies it would.
        # Not reachable through any current caller: every real construction
        # site (basejournalview._reset_model, called from listview.py's and
        # gridview.py's _do_refresh) calls .setup() synchronously right
        # after building the model and before it is ever wired to a view,
        # so no caller can reach set_value() first. Recorded as a fragile
        # invariant enforced only by call-site discipline, not the class.
        monkeypatch = _MonkeyPatch(self)
        lm, _rs = _make_model(monkeypatch, [{'uid': 'a', 'title': 'old'}])
        monkeypatch.setattr(model, 'write', lambda *a, **kw: None)
        with self.assertRaises(AttributeError):
            lm.set_value(_iter_at(0), listmodel.ListModel.COLUMN_TITLE, 'new')


# --- do_get_value / set_value interaction: the same-index read cache ---

class DoGetValueSetValueInteractionTest(unittest.TestCase):

    def test_do_get_value_after_set_value_serves_the_fresh_row(
            self):
        # set_value invalidates both row caches, so re-reading the edited
        # index sees the edit at once instead of the pre-edit cached row.
        monkeypatch = _MonkeyPatch(self)
        stub_misc(monkeypatch)
        lm, _rs = _make_model(
            monkeypatch,
            [{'uid': 'a', 'activity': 'x', 'title': 'old'},
             {'uid': 'b', 'activity': 'x', 'title': 'other'}])
        lm.setup(updated_callback=None)
        monkeypatch.setattr(model, 'write', lambda *a, **kw: None)
        column = listmodel.ListModel.COLUMN_TITLE

        self.assertEqual(lm.do_get_value(_iter_at(0), column), '<b>old</b>')
        lm.set_value(_iter_at(0), column, 'new')
        self.assertEqual(lm.do_get_value(_iter_at(0), column), '<b>new</b>')


if __name__ == '__main__':
    unittest.main()
