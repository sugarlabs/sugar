#!/usr/bin/env python
# Copyright (C) 2007, Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import os, time
import dbus
import gobject, gtk
import unittest
from sugar.presence import presenceservice

import mockps

def start_ps():
    argv = ["mockps.py", "mockps.py"]
    (pid, stdin, stdout, stderr) = gobject.spawn_async(argv, flags=gobject.SPAWN_LEAVE_DESCRIPTORS_OPEN)

    # Wait until it shows up on the bus
    tries = 0
    bus = dbus.SessionBus()
    while tries < 10:
        time.sleep(0.5)
        bus_object = bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
        try:
            if bus_object.GetNameOwner(presenceservice.DBUS_SERVICE, dbus_interface='org.freedesktop.DBus'):
                break
        except dbus.exceptions.DBusException, err:
            pass
        tries += 1

    if tries >= 5:
        stop_ps(pid)
        raise RuntimeError("Couldn't start the mock presence service")

    return pid

def stop_ps(pid):
    # EVIL HACK: get a new presence service object every time; close the
    # connection to completely clear all signal matches too
    presenceservice._ps._bus.close()
    del presenceservice._ps
    presenceservice._ps = None
    if pid >= 0:
        os.kill(pid, 15)

def get_ps():
    ps = presenceservice.get_instance(False)
    # HACK
    # Set exit on disconnect to False so we don't get aborted when
    # explicitly closing the bus connection in stop_ps()
    ps._bus.set_exit_on_disconnect(False)
    return ps


class GenericTestCase(unittest.TestCase):
    def setUp(self):
        self._pspid = start_ps()
        self._success = False
        self._err = ""
        self._signals = []
        self._sources = []

    def tearDown(self):
        # Remove all signal handlers
        for (obj, sid) in self._signals:
            obj.disconnect(sid)
        for source in self._sources:
            gobject.source_remove(source)

        if self._pspid > 0:
            stop_ps(self._pspid)
        self._pspid = -1

    def _handle_success(self):
        self._success = True
        gtk.main_quit()

    def _handle_error(self, err):
        self._success = False
        self._err = str(err)
        gtk.main_quit()

class BuddyTests(GenericTestCase):
    def _testOwner_helper(self):
        try:
            ps = get_ps()
        except RuntimeError, err:
            self._handle_error(err)
            return False
        
        try:
            owner = ps.get_owner()
        except RuntimeError, err:
            self._handle_error(err)
            return False

        self._owner = owner
        self._handle_success()
        return False

    def testOwner(self):
        gobject.idle_add(self._testOwner_helper)
        gtk.main()

        assert self._success == True, "Test unsuccessful."
        assert self._owner, "Owner could not be found."

        assert self._owner.props.key == mockps._OWNER_PUBKEY, "Owner public key doesn't match expected"
        assert self._owner.props.nick == mockps._OWNER_NICK, "Owner nickname doesn't match expected"
        assert self._owner.props.color == mockps._OWNER_COLOR, "Owner color doesn't match expected"

    _BA_PUBKEY = "akjadskjjfahfdahfdsahjfhfewaew3253232832832q098qewa98fdsafa98fa"
    _BA_NICK = "BuddyAppearedTestBuddy"
    _BA_COLOR = "#23adfb,#56bb11"

    def _testBuddyAppeared_helper_timeout(self):
        self._handle_error("Timeout waiting for buddy-appeared signal")
        return False

    def _testBuddyAppeared_helper_cb(self, ps, buddy):
        self._buddy = buddy
        self._handle_success()

    def _testBuddyAppeared_helper(self):
        ps = get_ps()
        sid = ps.connect('buddy-appeared', self._testBuddyAppeared_helper_cb)
        self._signals.append((ps, sid))
        # Wait 5 seconds max for signal to be emitted
        sid = gobject.timeout_add(5000, self._testBuddyAppeared_helper_timeout)
        self._sources.append(sid)

        busobj = dbus.SessionBus().get_object(mockps._PRESENCE_SERVICE,
                    mockps._PRESENCE_PATH)
        try:
            testps = dbus.Interface(busobj, mockps._PRESENCE_TEST_INTERFACE)
        except dbus.exceptions.DBusException, err:
            self._handle_error(err)
            return False

        try:
            testps.AddBuddy(self._BA_PUBKEY, self._BA_NICK, self._BA_COLOR)
        except dbus.exceptions.DBusException, err:
            self._handle_error(err)
            return False

        return False

    def testBuddyAppeared(self):
        ps = get_ps()
        assert ps, "Couldn't get presence service"

        self._buddy = None
        gobject.idle_add(self._testBuddyAppeared_helper)
        gtk.main()

        assert self._success == True, "Test unsuccessful."
        assert self._buddy, "Buddy was not received"

        assert self._buddy.props.key == self._BA_PUBKEY, "Public key doesn't match expected"
        assert self._buddy.props.nick == self._BA_NICK, "Nickname doesn't match expected"
        assert self._buddy.props.color == self._BA_COLOR, "Color doesn't match expected"

        # Try to get buddy by public key
        buddy2 = ps.get_buddy(self._BA_PUBKEY)
        assert buddy2, "Couldn't get buddy by public key"
        assert buddy2.props.key == self._BA_PUBKEY, "Public key doesn't match expected"
        assert buddy2.props.nick == self._BA_NICK, "Nickname doesn't match expected"
        assert buddy2.props.color == self._BA_COLOR, "Color doesn't match expected"

    def _testBuddyDisappeared_helper_timeout(self):
        self._handle_error("Timeout waiting for buddy-disappeared signal")
        return False

    def _testBuddyDisappeared_helper_cb(self, ps, buddy):
        self._buddy = buddy
        self._handle_success()

    def _testBuddyDisappeared_helper(self):
        busobj = dbus.SessionBus().get_object(mockps._PRESENCE_SERVICE,
                    mockps._PRESENCE_PATH)
        try:
            testps = dbus.Interface(busobj, mockps._PRESENCE_TEST_INTERFACE)
        except dbus.exceptions.DBusException, err:
            self._handle_error(err)
            return False

        # Add a fake buddy
        try:
            testps.AddBuddy(self._BA_PUBKEY, self._BA_NICK, self._BA_COLOR)
        except dbus.exceptions.DBusException, err:
            self._handle_error(err)
            return False

        ps = get_ps()
        sid = ps.connect('buddy-disappeared', self._testBuddyDisappeared_helper_cb)
        self._signals.append((ps, sid))

        # Wait 5 seconds max for signal to be emitted
        sid = gobject.timeout_add(5000, self._testBuddyDisappeared_helper_timeout)
        self._sources.append(sid)

        # Delete the fake buddy
        try:
            testps.RemoveBuddy(self._BA_PUBKEY)
        except dbus.exceptions.DBusException, err:
            self._handle_error(err)
            return False

        return False

    def testBuddyDisappeared(self):
        ps = get_ps()
        assert ps, "Couldn't get presence service"

        self._buddy = None
        gobject.idle_add(self._testBuddyDisappeared_helper)
        gtk.main()

        assert self._success == True, "Test unsuccessful."
        assert self._buddy, "Buddy was not received"

        assert self._buddy.props.key == self._BA_PUBKEY, "Public key doesn't match expected"
        assert self._buddy.props.nick == self._BA_NICK, "Nickname doesn't match expected"
        assert self._buddy.props.color == self._BA_COLOR, "Color doesn't match expected"

    def addToSuite(suite):
        suite.addTest(BuddyTests("testOwner"))
        suite.addTest(BuddyTests("testBuddyAppeared"))
        suite.addTest(BuddyTests("testBuddyDisappeared"))
    addToSuite = staticmethod(addToSuite)

class MockSugarActivity(gobject.GObject):
    __gproperties__ = {
        'title'     : (str, None, None, None, gobject.PARAM_READABLE)
    }

    def __init__(self, actid, name, atype):
        self._actid = actid
        self._name = name
        self._type = atype
        gobject.GObject.__init__(self)

    def do_get_property(self, pspec):
        if pspec.name == "title":
            return self._name

    def get_id(self):
        return self._actid

    def get_service_name(self):
        return self._type

class ActivityTests(GenericTestCase):
    _AA_ID = "d622b99b9f365d712296094b9f6110521e6c9cba"
    _AA_NAME = "Test Activity"
    _AA_TYPE = "org.laptop.Sugar.Foobar"
    _AA_COLOR = "#adfe20,#bf781a"
    _AA_PROPS = {"foo": "asdfadf", "bar":"5323aggdas"}

    def _testActivityAppeared_helper_timeout(self):
        self._handle_error("Timeout waiting for activity-appeared signal")
        return False

    def _testActivityAppeared_helper_cb(self, ps, activity):
        self._activity = activity
        self._handle_success()

    def _testActivityAppeared_helper(self):
        ps = get_ps()
        sid = ps.connect('activity-appeared', self._testActivityAppeared_helper_cb)
        self._signals.append((ps, sid))

        # Wait 5 seconds max for signal to be emitted
        sid = gobject.timeout_add(5000, self._testActivityAppeared_helper_timeout)
        self._sources.append(sid)

        busobj = dbus.SessionBus().get_object(mockps._PRESENCE_SERVICE,
                    mockps._PRESENCE_PATH)
        try:
            testps = dbus.Interface(busobj, mockps._PRESENCE_TEST_INTERFACE)
        except dbus.exceptions.DBusException, err:
            self._handle_error(err)
            return False

        try:
            testps.AddActivity(self._AA_ID, self._AA_NAME, self._AA_COLOR, self._AA_TYPE, {})
        except dbus.exceptions.DBusException, err:
            self._handle_error(err)
            return False

        return False

    def testActivityAppeared(self):
        ps = get_ps()
        assert ps, "Couldn't get presence service"

        self._activity = None
        gobject.idle_add(self._testActivityAppeared_helper)
        gtk.main()

        assert self._success == True, "Test unsuccessful"
        assert self._activity, "Activity was not received"

        assert self._activity.props.id == self._AA_ID, "ID doesn't match expected"
        assert self._activity.props.name == self._AA_NAME, "Name doesn't match expected"
        assert self._activity.props.color == self._AA_COLOR, "Color doesn't match expected"
        assert self._activity.props.type == self._AA_TYPE, "Type doesn't match expected"
        assert self._activity.props.joined == False, "Joined doesn't match expected"

        # Try to get activity by activity ID
        act2 = ps.get_activity(self._AA_ID)
        assert act2.props.id == self._AA_ID, "ID doesn't match expected"
        assert act2.props.name == self._AA_NAME, "Name doesn't match expected"
        assert act2.props.color == self._AA_COLOR, "Color doesn't match expected"
        assert act2.props.type == self._AA_TYPE, "Type doesn't match expected"
        assert act2.props.joined == False, "Joined doesn't match expected"

    def _testActivityDisappeared_helper_timeout(self):
        self._handle_error("Timeout waiting for activity-disappeared signal")
        return False

    def _testActivityDisappeared_helper_cb(self, ps, activity):
        self._activity = activity
        self._handle_success()

    def _testActivityDisappeared_helper(self):
        busobj = dbus.SessionBus().get_object(mockps._PRESENCE_SERVICE,
                    mockps._PRESENCE_PATH)
        try:
            testps = dbus.Interface(busobj, mockps._PRESENCE_TEST_INTERFACE)
        except dbus.exceptions.DBusException, err:
            self._handle_error(err)
            return False

        # Add a fake activity
        try:
            testps.AddActivity(self._AA_ID, self._AA_NAME, self._AA_COLOR, self._AA_TYPE, {})
        except dbus.exceptions.DBusException, err:
            self._handle_error(err)
            return False

        ps = get_ps()
        sid = ps.connect('activity-disappeared', self._testActivityDisappeared_helper_cb)
        self._signals.append((ps, sid))

        # Wait 5 seconds max for signal to be emitted
        sid = gobject.timeout_add(5000, self._testActivityDisappeared_helper_timeout)
        self._sources.append(sid)

        # Delete the fake activity
        try:
            testps.RemoveActivity(self._AA_ID)
        except dbus.exceptions.DBusException, err:
            self._handle_error(err)
            return False

        return False

    def testActivityDisappeared(self):
        ps = get_ps()
        assert ps, "Couldn't get presence service"

        self._activity = None
        gobject.idle_add(self._testActivityDisappeared_helper)
        gtk.main()

        assert self._success == True, "Test unsuccessful"
        assert self._activity, "Activity was not received"

        assert self._activity.props.id == self._AA_ID, "ID doesn't match expected"
        assert self._activity.props.name == self._AA_NAME, "Name doesn't match expected"
        assert self._activity.props.color == self._AA_COLOR, "Color doesn't match expected"
        assert self._activity.props.type == self._AA_TYPE, "Type doesn't match expected"
        assert self._activity.props.joined == False, "Joined doesn't match expected"

    def _testActivityShare_helper_is_done(self):
        if self._got_act_appeared and self._got_joined_activity:
            self._handle_success()

    def _testActivityShare_helper_timeout(self):
        self._handle_error("Timeout waiting for activity share")
        return False

    def _testActivityShare_helper_joined_activity_cb(self, buddy, activity):
        self._joined_activity_buddy = buddy
        self._joined_activity_activity = activity
        self._got_joined_activity = True
        self._testActivityShare_helper_is_done()

    def _testActivityShare_helper_cb(self, ps, activity):
        self._activity = activity
        self._got_act_appeared = True
        self._testActivityShare_helper_is_done()

    def _testActivityShare_helper(self):
        ps = get_ps()
        mockact = MockSugarActivity(self._AA_ID, self._AA_NAME, self._AA_TYPE)

        sid = ps.connect('activity-appeared', self._testActivityShare_helper_cb)
        self._signals.append((ps, sid))
        try:
            # Hook up to the owner's joined-activity signal
            owner = ps.get_owner()
            sid = owner.connect("joined-activity", self._testActivityShare_helper_joined_activity_cb)
            self._signals.append((owner, sid))
        except RuntimeError, err:
            self._handle_error(err)
            return False

        # Wait 5 seconds max for signal to be emitted
        sid = gobject.timeout_add(5000, self._testActivityShare_helper_timeout)
        self._sources.append(sid)

        ps.share_activity(mockact, self._AA_PROPS)

        return False

    def testActivityShare(self):
        ps = get_ps()
        assert ps, "Couldn't get presence service"

        self._activity = None
        self._got_act_appeared = False
        self._joined_activity_buddy = None
        self._joined_activity_activity = None
        self._got_joined_activity = False
        gobject.idle_add(self._testActivityShare_helper)
        gtk.main()

        assert self._success == True, "Test unsuccessful."
        assert self._activity, "Shared activity was not received"

        assert self._activity.props.id == self._AA_ID, "ID doesn't match expected"
        assert self._activity.props.name == self._AA_NAME, "Name doesn't match expected"
        # Shared activities from local machine take the owner's color
        assert self._activity.props.color == mockps._OWNER_COLOR, "Color doesn't match expected"
        assert self._activity.props.type == self._AA_TYPE, "Type doesn't match expected"
        assert self._activity.props.joined == False, "Joined doesn't match expected"

        buddies = self._activity.get_joined_buddies()
        assert len(buddies) == 1, "No buddies in activity"
        owner = buddies[0]
        assert owner.props.key == mockps._OWNER_PUBKEY, "Buddy key doesn't match expected"
        assert owner.props.nick == mockps._OWNER_NICK, "Buddy nick doesn't match expected"
        assert owner.props.color == mockps._OWNER_COLOR, "Buddy color doesn't match expected"

        real_owner = ps.get_owner()
        assert real_owner == owner, "Owner mismatch"

        assert self._joined_activity_activity == self._activity, "Activity mismatch"
        assert self._joined_activity_buddy == owner, "Owner mismatch"

    def _testActivityJoin_helper_is_done(self):
        if self._got_act_appeared and self._got_joined_activity and \
                self._got_buddy_joined:
            self._handle_success()

    def _testActivityJoin_helper_timeout(self):
        self._handle_error("Timeout waiting for activity share")
        return False

    def _testActivityJoin_helper_buddy_joined_cb(self, activity, buddy):
        self._buddy_joined_buddy = buddy
        self._buddy_joined_activity = activity
        self._got_buddy_joined = True
        self._testActivityJoin_helper_is_done()

    def _testActivityJoin_helper_joined_activity_cb(self, buddy, activity):
        self._joined_activity_buddy = buddy
        self._joined_activity_activity = activity
        self._got_joined_activity = True
        self._testActivityJoin_helper_is_done()

    def _testActivityJoin_helper_cb(self, ps, activity):
        self._activity = activity
        self._got_act_appeared = True

        # Hook up to the join signals
        sid = activity.connect("buddy-joined", self._testActivityJoin_helper_buddy_joined_cb)
        self._signals.append((activity, sid))

        ps = get_ps()
        owner = ps.get_owner()
        sid = owner.connect("joined-activity", self._testActivityJoin_helper_joined_activity_cb)
        self._signals.append((owner, sid))

        # Join the activity
        activity.join()

    def _testActivityJoin_helper(self):
        busobj = dbus.SessionBus().get_object(mockps._PRESENCE_SERVICE,
                    mockps._PRESENCE_PATH)
        try:
            testps = dbus.Interface(busobj, mockps._PRESENCE_TEST_INTERFACE)
        except dbus.exceptions.DBusException, err:
            self._handle_error(err)
            return False

        ps = get_ps()
        sid = ps.connect('activity-appeared', self._testActivityJoin_helper_cb)
        self._signals.append((ps, sid))

        # Add a fake activity
        try:
            testps.AddActivity(self._AA_ID, self._AA_NAME, self._AA_COLOR, self._AA_TYPE, {})
        except dbus.exceptions.DBusException, err:
            self._handle_error(err)
            return False

        # Wait 5 seconds max for signal to be emitted
        sid = gobject.timeout_add(5000, self._testActivityJoin_helper_timeout)
        self._sources.append(sid)

        return False

    def testActivityJoin(self):
        ps = get_ps()
        assert ps, "Couldn't get presence service"

        self._activity = None
        self._got_act_appeared = False
        self._joined_activity_buddy = None
        self._joined_activity_activity = None
        self._got_joined_activity = False
        self._buddy_joined_buddy = None
        self._buddy_joined_activity = None
        self._got_buddy_joined = False
        gobject.idle_add(self._testActivityJoin_helper)
        gtk.main()

        assert self._success == True, "Test unsuccessful"
        assert self._activity, "Shared activity was not received"

        assert self._activity.props.id == self._AA_ID, "ID doesn't match expected"
        assert self._activity.props.name == self._AA_NAME, "Name doesn't match expected"

        buddies = self._activity.get_joined_buddies()
        assert len(buddies) == 1, "No buddies in activity"
        owner = buddies[0]
        assert owner.props.key == mockps._OWNER_PUBKEY, "Buddy key doesn't match expected"
        assert owner.props.nick == mockps._OWNER_NICK, "Buddy nick doesn't match expected"
        assert owner.props.color == mockps._OWNER_COLOR, "Buddy color doesn't match expected"

        real_owner = ps.get_owner()
        assert real_owner == owner, "Owner mismatch"

        assert self._joined_activity_activity == self._activity, "Activity mismatch"
        assert self._joined_activity_buddy == owner, "Owner mismatch"
        assert self._buddy_joined_activity == self._activity, "Activity mismatch"
        assert self._buddy_joined_buddy == owner, "Owner mismatch"

    def _testCurrentActivity_helper_timeout(self):
        self._handle_error("Timeout waiting for current activity")
        return False

    def _testCurrentActivity_set_current_activity(self, actid):
        busobj = dbus.SessionBus().get_object(mockps._PRESENCE_SERVICE,
                    mockps._PRESENCE_PATH)
        try:
            testps = dbus.Interface(busobj, mockps._PRESENCE_TEST_INTERFACE)
            testps.SetBuddyCurrentActivity(self._buddy.props.key, actid)
        except dbus.exceptions.DBusException, err:
            self._handle_error(err)
            return

    def _testCurrentActivity_buddy_property_changed_cb(self, buddy, proplist):
        if not self._start_monitor:
            return
        if not 'current-activity' in proplist:
            return
        buddy_curact = buddy.props.current_activity
        if buddy_curact.props.id == self._AA_ID:
            self._got_first_curact = True
            # set next current activity
            self._testCurrentActivity_set_current_activity(self._other_actid)
        elif buddy_curact.props.id == self._other_actid:
            self._got_other_curact = True

        if self._got_first_curact and self._got_other_curact:
            self._handle_success()

    def _testCurrentActivity_start_monitor_helper(self):
        if len(self._activities) != 2 or not self._buddy:
            return
        self._start_monitor = True
        # Set first current activity
        self._testCurrentActivity_set_current_activity(self._AA_ID)
        
    def _testCurrentActivity_activity_helper_cb(self, ps, activity):
        if activity in self._activities:
            self._handle_error("Activity %s already known." % activity.props.id)
        self._activities.append(activity)
        self._testCurrentActivity_start_monitor_helper()

    def _testCurrentActivity_buddy_helper_cb(self, ps, buddy):
        self._buddy = buddy
        sid = buddy.connect("property-changed", self._testCurrentActivity_buddy_property_changed_cb)
        self._signals.append((buddy, sid))
        self._testCurrentActivity_start_monitor_helper()

    def _testCurrentActivity_helper(self):
        busobj = dbus.SessionBus().get_object(mockps._PRESENCE_SERVICE,
                    mockps._PRESENCE_PATH)
        try:
            testps = dbus.Interface(busobj, mockps._PRESENCE_TEST_INTERFACE)
        except dbus.exceptions.DBusException, err:
            self._handle_error(err)
            return False

        ps = get_ps()
        sid = ps.connect('activity-appeared', self._testCurrentActivity_activity_helper_cb)
        self._signals.append((ps, sid))
        sid = ps.connect('buddy-appeared', self._testCurrentActivity_buddy_helper_cb)
        self._signals.append((ps, sid))

        # Add a fake buddy
        try:
            testps.AddBuddy(BuddyTests._BA_PUBKEY, BuddyTests._BA_NICK, BuddyTests._BA_COLOR)
        except dbus.exceptions.DBusException, err:
            self._handle_error(err)
            return False

        # Add first fake activity
        try:
            testps.AddActivity(self._AA_ID, self._AA_NAME, self._AA_COLOR, self._AA_TYPE, {})
            testps.AddBuddyToActivity(BuddyTests._BA_PUBKEY, self._AA_ID)
        except dbus.exceptions.DBusException, err:
            self._handle_error(err)
            return False

        # Add second fake activity
        try:
            testps.AddActivity(self._other_actid, self._other_actname, 
                    self._other_actcolor, self._AA_TYPE, {})
            testps.AddBuddyToActivity(BuddyTests._BA_PUBKEY, self._other_actid)
        except dbus.exceptions.DBusException, err:
            self._handle_error(err)
            return False

        # Wait 10 seconds max for everything to complete
        sid = gobject.timeout_add(10000, self._testCurrentActivity_helper_timeout)
        self._sources.append(sid)

        return False

    def testCurrentActivity(self):
        ps = get_ps()
        assert ps, "Couldn't get presence service"

        self._other_actid = "ea8a94522c53a6741e141adece1711e4d9884678"
        self._other_actname = "Some random activity"
        self._other_actcolor = "#073838,#3A6E3A"
        self._activities = []
        self._got_first_curact = False
        self._got_other_curact = False
        self._start_monitor = False
        gobject.idle_add(self._testCurrentActivity_helper)
        gtk.main()

        assert self._success == True, "Test unsuccessful"
        assert len(self._activities) == 2, "Shared activities were not received"
        assert self._got_first_curact == True, "Couldn't discover first activity"
        assert self._got_other_curact == True, "Couldn't discover second activity"
        assert self._start_monitor == True, "Couldn't discover both activities"

        # check the buddy
        assert self._buddy.props.key == BuddyTests._BA_PUBKEY, "Buddy key doesn't match expected"
        assert self._buddy.props.nick == BuddyTests._BA_NICK, "Buddy nick doesn't match expected"
        assert self._buddy.props.color == BuddyTests._BA_COLOR, "Buddy color doesn't match expected"
        assert self._buddy.props.current_activity.props.id == self._other_actid, "Buddy current activity didn't match expected"

        # check both activities
        found = 0
        for act in self._activities:
            if act.props.id == self._AA_ID:
                assert act.props.name == self._AA_NAME, "Name doesn't match expected"
                assert act.props.color == self._AA_COLOR, "Color doesn't match expected"
                buddies = act.get_joined_buddies()
                assert len(buddies) == 1, "Unexpected number of buddies in first activity"
                assert buddies[0] == self._buddy, "Unexpected buddy in first activity"
                found += 1
            elif act.props.id == self._other_actid:
                assert act.props.name == self._other_actname, "Name doesn't match expected"
                assert act.props.color == self._other_actcolor, "Color doesn't match expected"
                buddies = act.get_joined_buddies()
                assert len(buddies) == 1, "Unexpected number of buddies in first activity"
                assert buddies[0] == self._buddy, "Unexpected buddy in first activity"
                found += 1

        assert found == 2, "Couldn't discover both activities"

    def addToSuite(suite):
        suite.addTest(ActivityTests("testActivityAppeared"))
        suite.addTest(ActivityTests("testActivityDisappeared"))
        suite.addTest(ActivityTests("testActivityShare"))
        suite.addTest(ActivityTests("testActivityJoin"))
        suite.addTest(ActivityTests("testCurrentActivity"))
    addToSuite = staticmethod(addToSuite)

def main():
    import logging
    logging.basicConfig(level=logging.DEBUG)

    suite = unittest.TestSuite()
    BuddyTests.addToSuite(suite)
    ActivityTests.addToSuite(suite)
    runner = unittest.TextTestRunner()
    runner.run(suite)

if __name__ == "__main__":
    main()
