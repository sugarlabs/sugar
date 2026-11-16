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
import types
import unittest
from unittest.mock import Mock

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
    0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# jarabe.desktop.meshbox drags in three things this host does not
# have: jarabe.config is generated at build time; xapian is not apt
# installed here; jarabe.view.viewsource hard-pins GtkSource 3.0 and
# the host only carries 4 on the girepository path. None of the three
# is needed to exercise the widget logic under test, so each is
# stubbed only when the real thing is missing.
try:
    import jarabe.config  # noqa: E402,F401
except ImportError:
    _config_stub = types.ModuleType('jarabe.config')
    _config_stub.prefix = '/usr'
    _config_stub.data_path = '/usr/share/sugar'
    _config_stub.version = '0.999'
    sys.modules['jarabe.config'] = _config_stub

try:
    import xapian  # noqa: E402,F401
except ImportError:
    sys.modules['xapian'] = types.ModuleType('xapian')

try:
    import jarabe.view.viewsource  # noqa: E402,F401
except (ImportError, ValueError):
    _viewsource_stub = types.ModuleType('jarabe.view.viewsource')
    _viewsource_stub.setup_view_source = lambda activity: None
    sys.modules['jarabe.view.viewsource'] = _viewsource_stub

# meshbox <-> buddyicon <-> buddymenu <-> homewindow <-> meshbox is a
# real circular import; homewindow imports MeshBox itself, so priming
# sys.modules with it first lets meshbox finish initializing before
# buddymenu asks for the (still loading) name a second time.
import jarabe.desktop.homewindow  # noqa: E402,F401

from gi.repository import Gdk  # noqa: E402
from gi.repository import Gtk  # noqa: E402

from jarabe.desktop.meshbox import MeshBox  # noqa: E402
from jarabe.desktop.meshbox import _SharedEntriesGroup  # noqa: E402
from jarabe.desktop.meshbox import _SharedEntryIcon  # noqa: E402
from jarabe.model import neighborhood  # noqa: E402
from jarabe.view.buddyicon import BuddyIcon  # noqa: E402


class _Owner(object):
    class props:
        key = 'owner-1'


class _FilterableBox(Gtk.EventBox):
    """A center widget with the set_filter() method the group expects
    on every child, including the center."""

    def set_filter(self, query):
        pass


def _rect(width=50, height=50):
    rect = Gdk.Rectangle()
    rect.x = 0
    rect.y = 0
    rect.width = width
    rect.height = height
    return rect


def _owner_buddy(key='owner-1', nick='Ana', handle=9):
    return neighborhood.BuddyModel(nick=nick, key=key, account='/salut',
                                   contact_id='%s@laptop' % nick.lower(),
                                   handle=handle)


class _SelfOwnedBuddyModel(neighborhood.BuddyModel):
    """A BuddyModel whose is_owner() answers True, the way the real
    OwnerBuddyModel does -- BuddyModel itself always answers False, so
    exercising the is_owner() branch of _group_for needs this override.
    """

    def is_owner(self):
        return True


def _shared_activity(activity_id, uid, owner):
    activity = neighborhood.ActivityModel(activity_id, 7)
    activity.entry_uid = uid
    activity.add_buddy(owner)
    return activity


class _FakeBox(object):
    """Stands in for MeshBox itself when driving _group_for,
    _dissolve_group and _adopt_entries.

    MeshBox is a real Gtk.Container, but only _SharedEntriesGroup
    got the 585c1a47 hardening -- MeshBox's own do_forall is still
    unguarded. A bare MeshBox built for a test hits GTK's container
    dispose path once its last Python reference drops, and runs into
    the same unguarded `self._children` access the teardown-guard
    tests below check for -- except on MeshBox nothing catches it.

    Running the three grouping methods as unbound functions against
    this plain double avoids that GTK lifecycle. That's fine here:
    the methods are just dict bookkeeping over
    _buddies/_activities/_entry_groups, and the widgets they build
    (_SharedEntriesGroup, BuddyIcon, _SharedEntryIcon) are real and
    guarded on their own.
    """

    # These are plain methods, no GTK vfunc dispatch involved, so the
    # real unbound implementations work fine against this duck-typed
    # self -- including _adopt_entries' call to the name-mangled
    # self.__entry_owner_notify_cb, aliased under its mangled name.
    _group_for = MeshBox._group_for
    _dissolve_group = MeshBox._dissolve_group
    _adopt_entries = MeshBox._adopt_entries
    _MeshBox__entry_owner_notify_cb = MeshBox._MeshBox__entry_owner_notify_cb

    def __init__(self):
        self._buddies = {}
        self._activities = {}
        self._entry_groups = {}
        self._query = ''
        self._model = Mock()
        self._children = []

    def add(self, widget):
        self._children.append(widget)

    def remove(self, widget):
        if widget in self._children:
            self._children.remove(widget)


class _WidgetTestCase(unittest.TestCase):
    """Destroys every real GTK widget it builds before the test
    method returns, instead of leaving it for the garbage collector.
    GC timing isn't deterministic, and for the one container here
    that isn't hardened (see _FakeBox) that can reproduce the exact
    crash these tests are guarding against.
    """

    def _make_group(self):
        group = _SharedEntriesGroup(_Owner(), _FilterableBox())
        entry = Gtk.EventBox()
        group.add_entry('activity-1', entry)
        self.addCleanup(group.destroy)
        return group, entry

    def _offscreen_window(self):
        window = Gtk.OffscreenWindow()
        self.addCleanup(window.destroy)
        return window


# GTK walks a container's children once more while it is torn down,
# after the Python wrapper has lost its own attributes; every vfunc
# that reaches into self._children shares that risk (meshbox.py,
# comment above do_forall). These regression-test the exact trigger:
# a group with `_children` gone still answers every guarded vfunc.

class TestSharedEntriesGroupTeardownGuard(_WidgetTestCase):

    def test_do_forall_on_a_torn_down_group_visits_nothing(self):
        group, _entry = self._make_group()
        del group._children
        seen = []
        group.do_forall(True, seen.append)
        self.assertEqual(seen, [])

    def test_do_size_allocate_on_a_torn_down_group_does_not_crash(self):
        group, _entry = self._make_group()
        del group._children
        group.do_size_allocate(_rect())

    def test_get_radius_on_a_torn_down_group_is_zero(self):
        group, _entry = self._make_group()
        del group._children
        self.assertEqual(group._get_radius(), 0)

    def test_calculate_size_on_a_torn_down_group_is_zero(self):
        group, _entry = self._make_group()
        del group._children
        self.assertEqual(group._calculate_size(), 0)

    def test_do_realize_on_a_torn_down_group_does_not_crash(self):
        # do_realize needs a real parent window before the guarded
        # loop is even reached, so this parents the group for real
        # first and only then removes _children underneath it.
        window = self._offscreen_window()
        group, _entry = self._make_group()
        window.add(group)
        window.show_all()
        del group._children
        group.do_realize()


class TestSharedEntriesGroupNormalBehavior(_WidgetTestCase):

    def test_do_forall_visits_the_center_and_every_entry(self):
        group, entry = self._make_group()
        seen = []
        group.do_forall(True, seen.append)
        self.assertEqual(set(seen), {group._center, entry})

    def test_size_allocate_and_size_queries_do_not_crash(self):
        window = self._offscreen_window()
        group, _entry = self._make_group()
        window.add(group)
        window.show_all()
        group.do_size_allocate(_rect())
        self.assertGreater(group._get_radius(), 0)
        self.assertGreater(group._calculate_size(), 0)

    def test_has_entry_and_entry_ids_track_what_was_added(self):
        group, _entry = self._make_group()
        self.assertTrue(group.has_entry('activity-1'))
        self.assertEqual(group.entry_ids(), ['activity-1'])
        self.assertFalse(group.is_empty())

    def test_remove_entry_leaves_the_group_empty(self):
        group, _entry = self._make_group()
        group.remove_entry('activity-1')
        self.assertFalse(group.has_entry('activity-1'))
        self.assertTrue(group.is_empty())

    def test_positioning_data_is_keyed_on_the_owner(self):
        group, _entry = self._make_group()
        self.assertEqual(group.get_positioning_data(),
                         'entries-of-owner-1')


class TestGroupFor(unittest.TestCase):

    def test_the_owners_standalone_icon_is_replaced_by_a_group(self):
        box = _FakeBox()
        owner = _owner_buddy()
        standalone = BuddyIcon(owner)
        box._buddies[owner.props.key] = standalone
        box.add(standalone)
        activity = _shared_activity('a1', 'uid-1', owner)

        group = box._group_for(activity)

        self.assertIsInstance(group, _SharedEntriesGroup)
        self.assertIs(box._buddies[owner.props.key], group)
        self.assertIs(box._entry_groups[owner.props.key], group)

    def test_a_second_call_for_the_same_owner_reuses_the_group(self):
        box = _FakeBox()
        owner = _owner_buddy()
        standalone = BuddyIcon(owner)
        box._buddies[owner.props.key] = standalone
        box.add(standalone)
        activity = _shared_activity('a1', 'uid-1', owner)

        first = box._group_for(activity)
        second = box._group_for(activity)
        self.assertIs(first, second)

    def test_no_standalone_icon_means_no_group_yet(self):
        box = _FakeBox()
        owner = _owner_buddy()
        activity = _shared_activity('a1', 'uid-1', owner)
        self.assertIsNone(box._group_for(activity))

    def test_the_owner_of_their_own_entry_never_groups(self):
        box = _FakeBox()
        # The owner already has a standalone icon in _buddies, same as
        # any other buddy would -- so the only thing standing between
        # this activity and a fresh group is the is_owner() check
        # itself, not the `key not in self._buddies` guard below it.
        owner = _SelfOwnedBuddyModel(nick='Ana', key='owner-self',
                                     account='/salut',
                                     contact_id='ana@laptop', handle=9)
        standalone = BuddyIcon(owner)
        box._buddies[owner.props.key] = standalone
        box.add(standalone)
        activity = _shared_activity('a1', 'uid-1', owner)

        self.assertIsNone(box._group_for(activity))

        self.assertIs(box._buddies[owner.props.key], standalone)
        self.assertNotIn(owner.props.key, box._entry_groups)

    def test_an_ownerless_entry_never_groups(self):
        box = _FakeBox()
        activity = neighborhood.ActivityModel('a1', 7)
        activity.entry_uid = 'uid-1'
        self.assertIsNone(box._group_for(activity))


class TestDissolveGroup(unittest.TestCase):

    def test_dissolving_keeps_the_buddy_as_a_plain_icon(self):
        box = _FakeBox()
        owner = _owner_buddy()
        standalone = BuddyIcon(owner)
        box._buddies[owner.props.key] = standalone
        box.add(standalone)
        activity = _shared_activity('a1', 'uid-1', owner)
        group = box._group_for(activity)
        entry_icon = _SharedEntryIcon(activity)
        group.add_entry(activity.activity_id, entry_icon)
        box._activities[activity.activity_id] = entry_icon

        box._dissolve_group(owner.props.key, keep_buddy=True)

        self.assertNotIn(owner.props.key, box._entry_groups)
        self.assertIsInstance(box._buddies[owner.props.key], BuddyIcon)
        self.assertIn(activity.activity_id, box._activities)
        self.assertIsNot(box._activities[activity.activity_id], entry_icon)

    def test_dissolving_without_keeping_drops_the_buddy_entirely(self):
        box = _FakeBox()
        owner = _owner_buddy()
        standalone = BuddyIcon(owner)
        box._buddies[owner.props.key] = standalone
        box.add(standalone)
        activity = _shared_activity('a1', 'uid-1', owner)
        box._group_for(activity)

        box._dissolve_group(owner.props.key, keep_buddy=False)

        self.assertNotIn(owner.props.key, box._buddies)
        self.assertNotIn(owner.props.key, box._entry_groups)

    def test_entries_left_in_the_group_scatter_as_standalone_icons(self):
        box = _FakeBox()
        owner = _owner_buddy()
        standalone = BuddyIcon(owner)
        box._buddies[owner.props.key] = standalone
        box.add(standalone)
        activity = _shared_activity('a1', 'uid-1', owner)
        group = box._group_for(activity)
        entry_icon = _SharedEntryIcon(activity)
        group.add_entry(activity.activity_id, entry_icon)
        box._activities[activity.activity_id] = entry_icon

        box._dissolve_group(owner.props.key, keep_buddy=False)

        self.assertIsInstance(
            box._activities[activity.activity_id], _SharedEntryIcon)


class TestAdoptEntries(unittest.TestCase):

    def test_a_standalone_entry_is_gathered_once_its_owner_gets_an_icon(
            self):
        box = _FakeBox()
        owner = _owner_buddy()
        standalone = BuddyIcon(owner)
        box._buddies[owner.props.key] = standalone
        box.add(standalone)
        activity = _shared_activity('a3', 'uid-3', owner)
        icon = _SharedEntryIcon(activity)
        box.add(icon)
        box._activities[activity.activity_id] = icon
        box._model.get_activities.return_value = [activity]

        box._adopt_entries(owner)

        self.assertIn(owner.props.key, box._entry_groups)
        self.assertIsInstance(
            box._activities[activity.activity_id], _SharedEntryIcon)
        self.assertIsNot(box._activities[activity.activity_id], icon)

    def test_entries_owned_by_somebody_else_are_left_alone(self):
        box = _FakeBox()
        owner = _owner_buddy(key='owner-1')
        other = _owner_buddy(key='owner-2', nick='Bo', handle=11)
        standalone = BuddyIcon(owner)
        box._buddies[owner.props.key] = standalone
        box.add(standalone)
        # `other` also has a standalone icon, so a group is just as
        # reachable for their entry as for the owner's -- if the
        # entry_uid/owner filter in _adopt_entries let it through,
        # _group_for would happily gather it too.
        other_standalone = BuddyIcon(other)
        box._buddies[other.props.key] = other_standalone
        box.add(other_standalone)
        # A group for `owner` already exists, seeded by an unrelated
        # entry, so `mine` below is adopted into an existing group
        # rather than a freshly-created one.
        seed = _shared_activity('a0', 'uid-0', owner)
        group = box._group_for(seed)

        mine = _shared_activity('a4', 'uid-4', owner)
        icon_mine = _SharedEntryIcon(mine)
        box.add(icon_mine)
        box._activities[mine.activity_id] = icon_mine

        theirs = _shared_activity('a5', 'uid-5', other)
        icon_theirs = _SharedEntryIcon(theirs)
        box.add(icon_theirs)
        box._activities[theirs.activity_id] = icon_theirs

        box._model.get_activities.return_value = [mine, theirs]

        box._adopt_entries(owner)

        self.assertTrue(group.has_entry(mine.activity_id))
        self.assertIsNot(box._activities[mine.activity_id], icon_mine)

        self.assertFalse(group.has_entry(theirs.activity_id))
        self.assertIs(box._activities[theirs.activity_id], icon_theirs)
        self.assertNotIn(other.props.key, box._entry_groups)
        self.assertIs(box._buddies[other.props.key], other_standalone)


if __name__ == '__main__':
    unittest.main()
