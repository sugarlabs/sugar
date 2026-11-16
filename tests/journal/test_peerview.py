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

import base64
import logging
import os
import sys
import types
import unittest
from unittest.mock import Mock, patch

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

# peerview.py reaches jarabe.journal.expandedentry -> jarabe.journal.
# palettes -> jarabe.webservice.accountsmanager -> `from jarabe import
# config`, which is generated at build time and absent on a bare
# checkout. Stubbed only when the real thing is missing.
try:
    import jarabe.config  # noqa: E402,F401
except ImportError:
    _config_stub = types.ModuleType('jarabe.config')
    _config_stub.prefix = '/usr'
    _config_stub.data_path = '/usr/share/sugar'
    _config_stub.version = '0.999'
    sys.modules['jarabe.config'] = _config_stub

from sugar3.graphics.xocolor import XoColor  # noqa: E402

from jarabe.journal import peerview  # noqa: E402
from jarabe.journal.peerview import _BorrowedPage  # noqa: E402
from jarabe.journal.peerview import _clean_text  # noqa: E402
from jarabe.journal.peerview import _preview_bytes  # noqa: E402
from jarabe.journal.peerview import PeerEntryView  # noqa: E402
from jarabe.model import neighborhood  # noqa: E402

_PNG_MAGIC = b'\x89PNG\r\n\x1a\n'

_TINY_PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8A'
    'AQUBAScY42YAAAAASUVORK5CYII=')


class TestCleanText(unittest.TestCase):

    def test_control_and_direction_characters_are_stripped(self):
        self.assertEqual(_clean_text('a\rb\u202ec'), 'abc')
        self.assertEqual(_clean_text('a\u2028b'), 'ab')

    def test_newlines_are_dropped_by_default(self):
        self.assertEqual(_clean_text('a\nb'), 'ab')

    def test_newlines_survive_when_multiline_is_asked_for(self):
        self.assertEqual(_clean_text('a\nb', multiline=True), 'a\nb')

    def test_a_non_string_becomes_empty(self):
        self.assertEqual(_clean_text(None), '')
        self.assertEqual(_clean_text(5), '')

    def test_ordinary_text_is_untouched(self):
        self.assertEqual(_clean_text('hello there'), 'hello there')


class TestPreviewBytes(unittest.TestCase):

    def test_a_valid_image_decodes(self):
        encoded = base64.b64encode(_TINY_PNG).decode()
        self.assertEqual(_preview_bytes(encoded), _TINY_PNG)

    def test_nothing_sent_is_nothing_to_show(self):
        self.assertIsNone(_preview_bytes(None))
        self.assertIsNone(_preview_bytes(''))

    def test_a_non_string_is_refused(self):
        self.assertIsNone(_preview_bytes(5))
        self.assertIsNone(_preview_bytes([1, 2, 3]))

    def test_an_oversized_payload_is_refused(self):
        # this is valid base64; the size cap is what refuses it here,
        # so a decode error would be the wrong failure mode
        oversized = base64.b64encode(
            b'x' * (peerview.peershare.PAYLOAD_LIMIT + 1)).decode()
        self.assertIsNone(_preview_bytes(oversized))

    def test_a_payload_at_the_limit_is_accepted(self):
        limit = peerview.peershare.PAYLOAD_LIMIT
        raw = _PNG_MAGIC + b'x' * (limit * 3 // 4 - len(_PNG_MAGIC))
        at_limit = base64.b64encode(raw).decode()
        self.assertEqual(len(at_limit), limit)
        self.assertEqual(_preview_bytes(at_limit), raw)

    def test_bytes_that_are_not_a_png_are_refused(self):
        # the toolkit's loader would try to base64-decode these again
        self.assertIsNone(_preview_bytes(base64.b64encode(b'AAAAA').decode()))

    def test_text_that_is_not_base64_is_refused(self):
        with self.assertLogs(level=logging.ERROR):
            self.assertIsNone(_preview_bytes('not base64 at all!!'))


class TestBorrowedPageSubtraction(unittest.TestCase):

    def _page(self):
        page = _BorrowedPage(XoColor('#FF2B34,#005FE4'))
        self.addCleanup(page.destroy)
        return page

    def test_the_page_is_never_editable(self):
        self.assertFalse(self._page()._entry_editable())

    def test_writing_is_a_dead_end(self):
        page = self._page()
        page._write_entry()

    def test_the_technical_line_is_an_empty_box(self):
        box = self._page()._create_technical()
        self.assertEqual(box.get_children(), [])

    def test_set_metadata_hides_the_keep_icon_and_the_date(self):
        page = self._page()
        page.set_metadata({
            'uid': 'abc', 'title': 'my rockit', 'description': '',
            'tags': '', 'activity': '', 'mime_type': '',
            'icon-color': '#FF2B34,#005FE4', 'comments': '[]'})
        for widget in (page._keep_icon, page._date):
            self.assertTrue(widget.get_no_show_all())
            self.assertFalse(widget.get_visible())


class _FakeNeighborhoodModel(object):
    """A stand-in for neighborhood.get_model() that lets a test fire
    'activity-removed'/'buddy-removed' by hand."""

    def __init__(self):
        self._callbacks = {}
        self._next_id = 0
        self.disconnected = []

    def connect(self, signal, callback):
        self._next_id += 1
        self._callbacks[self._next_id] = (signal, callback)
        return self._next_id

    def disconnect(self, handler_id):
        self.disconnected.append(handler_id)
        self._callbacks.pop(handler_id, None)

    def get_link_local_connection(self):
        # PeerEntryView's own wire is not what these tests exercise;
        # a missing connection sends _open_line straight to
        # _give_up(), so no dbus is ever touched.
        return None

    def fire(self, signal, *args):
        for handler_id, (sig, callback) in list(self._callbacks.items()):
            if sig == signal:
                callback(self, *args)


class _PeerViewTestCase(unittest.TestCase):

    def setUp(self):
        self.model = _FakeNeighborhoodModel()
        patcher = patch.object(peerview.neighborhood, 'get_model',
                               lambda: self.model)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _owner(self, key='owner-1', nick='Ana'):
        owner = Mock()
        owner.props.key = key
        owner.get_nick.return_value = nick
        owner.is_owner.return_value = False
        return owner

    def _activity(self, activity_id='a1', uid='uid-1', owner=None):
        activity = neighborhood.ActivityModel(activity_id, 7)
        activity.entry_uid = uid
        if owner is not None:
            activity.add_buddy(owner)
        return activity

    def _view(self, activity):
        view = PeerEntryView(activity)
        self.addCleanup(view.destroy)
        return view


class TestActivityRemovedPutsAway(_PeerViewTestCase):

    def test_a_different_activitys_removal_is_ignored(self):
        activity = self._activity(owner=self._owner())
        view = self._view(activity)
        other = self._activity(activity_id='a2', uid='uid-2')

        self.model.fire('activity-removed', other)

        self.assertFalse(view._put_away_done)

    def test_the_matching_activitys_removal_puts_it_away(self):
        activity = self._activity(owner=self._owner())
        view = self._view(activity)

        self.model.fire('activity-removed', activity)

        self.assertTrue(view._put_away_done)


class TestBuddyRemovedPutsAway(_PeerViewTestCase):

    def test_a_different_buddy_leaving_is_ignored(self):
        activity = self._activity(owner=self._owner(key='owner-1'))
        view = self._view(activity)
        someone_else = Mock()
        someone_else.props.key = 'someone-else'

        self.model.fire('buddy-removed', someone_else)

        self.assertFalse(view._put_away_done)

    def test_the_owner_leaving_puts_it_away(self):
        activity = self._activity(owner=self._owner(key='owner-1'))
        view = self._view(activity)
        the_owner = Mock()
        the_owner.props.key = 'owner-1'

        self.model.fire('buddy-removed', the_owner)

        self.assertTrue(view._put_away_done)

    def test_an_entry_with_no_owner_tolerates_any_buddy_leaving(self):
        activity = self._activity(owner=None)
        view = self._view(activity)
        self.assertIsNone(view._owner_key)
        somebody = Mock()
        somebody.props.key = 'anybody'

        self.model.fire('buddy-removed', somebody)

        self.assertFalse(view._put_away_done)


class TestPutAwayIsIdempotent(_PeerViewTestCase):

    def test_without_a_page_the_status_update_happens_once(self):
        activity = self._activity(owner=self._owner())
        view = self._view(activity)
        view._cancel_timeout = Mock()

        view._put_away()
        view._put_away()

        self.assertEqual(view._cancel_timeout.call_count, 1)
        self.assertTrue(view._put_away_done)

    def test_with_a_page_the_page_is_put_away_only_once(self):
        activity = self._activity(owner=self._owner())
        view = self._view(activity)
        view._page = Mock()
        view._ask_row = Mock()
        view._ask_column = Mock()
        view._ask_lead = Mock()
        view._ask_status = Mock()

        view._put_away()
        view._put_away()

        self.assertEqual(view._page.put_away.call_count, 1)
        # One _put_away call removes both the ask row and its lead;
        # the guard means that only happens for the first call.
        self.assertEqual(view._ask_column.remove.call_count, 2)
        self.assertIsNone(view._ask_row)


class TestDestroyDisconnectsBothWatches(_PeerViewTestCase):

    def test_both_handlers_are_let_go_on_destroy(self):
        activity = self._activity(owner=self._owner())
        view = PeerEntryView(activity)
        gone_id = view._gone_id
        buddy_gone_id = view._buddy_gone_id

        view.destroy()

        self.assertIn(gone_id, self.model.disconnected)
        self.assertIn(buddy_gone_id, self.model.disconnected)


if __name__ == '__main__':
    unittest.main()
