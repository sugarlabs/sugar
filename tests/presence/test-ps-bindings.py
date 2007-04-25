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
    # EVIL HACK: get a new presence service object every time
    del presenceservice._ps
    presenceservice._ps = None
    if pid >= 0:
        os.kill(pid, 15)
    

class GenericTestCase(unittest.TestCase):
    def setUp(self):
        self._pspid = start_ps()

    def tearDown(self):
        if self._pspid > 0:
            stop_ps(self._pspid)
        self._pspid = -1

    def _handle_error(self, err, user_data):
        user_data["success"] = False
        user_data["err"] = str(err)
        gtk.main_quit()


class BuddyTests(GenericTestCase):
    def _testOwner_helper(self, user_data):
        try:
            ps = presenceservice.get_instance(False)
        except RuntimeError, err:
            self._handle_error(err, user_data)
            return False
        
        try:
            owner = ps.get_owner()
        except RuntimeError, err:
            self._handle_error(err, user_data)
            return False

        user_data["success"] = True
        user_data["owner"] = owner
        gtk.main_quit()
        return False

    def testOwner(self):
        user_data = {"success": False, "err": "", "owner": None}
        gobject.idle_add(self._testOwner_helper, user_data)
        gtk.main()

        assert user_data["success"] == True, user_data["err"]
        assert user_data["owner"], "Owner could not be found."

        owner = user_data["owner"]
        assert owner.props.key == mockps._OWNER_PUBKEY, "Owner public key doesn't match expected"
        assert owner.props.nick == mockps._OWNER_NICK, "Owner nickname doesn't match expected"
        assert owner.props.color == mockps._OWNER_COLOR, "Owner color doesn't match expected"

    _BA_PUBKEY = "akjadskjjfahfdahfdsahjfhfewaew3253232832832q098qewa98fdsafa98fa"
    _BA_NICK = "BuddyAppearedTestBuddy"
    _BA_COLOR = "#23adfb,#56bb11"

    def _testBuddyAppeared_helper_timeout(self, user_data):
        self._handle_error("Timeout waiting for buddy-appeared signal", user_data)
        return False

    def _testBuddyAppeared_helper_cb(self, ps, buddy, user_data):
        user_data["buddy"] = buddy
        user_data["success"] = True
        gtk.main_quit()

    def _testBuddyAppeared_helper(self, user_data):
        ps = presenceservice.get_instance(False)
        ps.connect('buddy-appeared', self._testBuddyAppeared_helper_cb, user_data)
        # Wait 5 seconds max for signal to be emitted
        gobject.timeout_add(5000, self._testBuddyAppeared_helper_timeout, user_data)

        busobj = dbus.SessionBus().get_object(mockps._PRESENCE_SERVICE,
                    mockps._PRESENCE_PATH)
        try:
            testps = dbus.Interface(busobj, mockps._PRESENCE_TEST_INTERFACE)
        except dbus.exceptions.DBusException, err:
            self._handle_error(err, user_data)
            return False

        try:
            testps.AddBuddy(self._BA_PUBKEY, self._BA_NICK, self._BA_COLOR)
        except dbus.exceptions.DBusException, err:
            self._handle_error(err, user_data)
            return False

        return False

    def testBuddyAppeared(self):
        ps = presenceservice.get_instance(False)
        assert ps, "Couldn't get presence service"

        user_data = {"success": False, "err": "", "buddy": None}
        gobject.idle_add(self._testBuddyAppeared_helper, user_data)
        gtk.main()

        assert user_data["success"] == True, user_data["err"]
        assert user_data["buddy"], "Buddy was not received"

        buddy = user_data["buddy"]
        assert buddy.props.key == self._BA_PUBKEY, "Public key doesn't match expected"
        assert buddy.props.nick == self._BA_NICK, "Nickname doesn't match expected"
        assert buddy.props.color == self._BA_COLOR, "Color doesn't match expected"

        # Try to get buddy by public key
        buddy2 = ps.get_buddy(self._BA_PUBKEY)
        assert buddy2, "Couldn't get buddy by public key"
        assert buddy2.props.key == self._BA_PUBKEY, "Public key doesn't match expected"
        assert buddy2.props.nick == self._BA_NICK, "Nickname doesn't match expected"
        assert buddy2.props.color == self._BA_COLOR, "Color doesn't match expected"

    def _testBuddyDisappeared_helper_timeout(self, user_data):
        self._handle_error("Timeout waiting for buddy-disappeared signal", user_data)
        return False

    def _testBuddyDisappeared_helper_cb(self, ps, buddy, user_data):
        user_data["buddy"] = buddy
        user_data["success"] = True
        gtk.main_quit()

    def _testBuddyDisappeared_helper(self, user_data):
        busobj = dbus.SessionBus().get_object(mockps._PRESENCE_SERVICE,
                    mockps._PRESENCE_PATH)
        try:
            testps = dbus.Interface(busobj, mockps._PRESENCE_TEST_INTERFACE)
        except dbus.exceptions.DBusException, err:
            self._handle_error(err, user_data)
            return False

        # Add a fake buddy
        try:
            testps.AddBuddy(self._BA_PUBKEY, self._BA_NICK, self._BA_COLOR)
        except dbus.exceptions.DBusException, err:
            self._handle_error(err, user_data)
            return False

        ps = presenceservice.get_instance(False)
        ps.connect('buddy-disappeared', self._testBuddyDisappeared_helper_cb, user_data)
        # Wait 5 seconds max for signal to be emitted
        gobject.timeout_add(5000, self._testBuddyDisappeared_helper_timeout, user_data)

        # Delete the fake buddy
        try:
            testps.RemoveBuddy(self._BA_PUBKEY)
        except dbus.exceptions.DBusException, err:
            self._handle_error(err, user_data)
            return False

        return False

    def testBuddyDisappeared(self):
        ps = presenceservice.get_instance(False)
        assert ps, "Couldn't get presence service"

        user_data = {"success": False, "err": "", "buddy": None}
        gobject.idle_add(self._testBuddyDisappeared_helper, user_data)
        gtk.main()

        assert user_data["success"] == True, user_data["err"]
        assert user_data["buddy"], "Buddy was not received"

        buddy = user_data["buddy"]
        assert buddy.props.key == self._BA_PUBKEY, "Public key doesn't match expected"
        assert buddy.props.nick == self._BA_NICK, "Nickname doesn't match expected"
        assert buddy.props.color == self._BA_COLOR, "Color doesn't match expected"

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

    def _testActivityAppeared_helper_timeout(self, user_data):
        self._handle_error("Timeout waiting for activity-appeared signal", user_data)
        return False

    def _testActivityAppeared_helper_cb(self, ps, activity, user_data):
        user_data["activity"] = activity
        user_data["success"] = True
        gtk.main_quit()

    def _testActivityAppeared_helper(self, user_data):
        ps = presenceservice.get_instance(False)
        ps.connect('activity-appeared', self._testActivityAppeared_helper_cb, user_data)
        # Wait 5 seconds max for signal to be emitted
        gobject.timeout_add(5000, self._testActivityAppeared_helper_timeout, user_data)

        busobj = dbus.SessionBus().get_object(mockps._PRESENCE_SERVICE,
                    mockps._PRESENCE_PATH)
        try:
            testps = dbus.Interface(busobj, mockps._PRESENCE_TEST_INTERFACE)
        except dbus.exceptions.DBusException, err:
            self._handle_error(err, user_data)
            return False

        try:
            testps.AddActivity(self._AA_ID, self._AA_NAME, self._AA_COLOR, self._AA_TYPE, {})
        except dbus.exceptions.DBusException, err:
            self._handle_error(err, user_data)
            return False

        return False

    def testActivityAppeared(self):
        ps = presenceservice.get_instance(False)
        assert ps, "Couldn't get presence service"

        user_data = {"success": False, "err": "", "activity": None}
        gobject.idle_add(self._testActivityAppeared_helper, user_data)
        gtk.main()

        assert user_data["success"] == True, user_data["err"]
        assert user_data["activity"], "Activity was not received"

        act = user_data["activity"]
        assert act.props.id == self._AA_ID, "ID doesn't match expected"
        assert act.props.name == self._AA_NAME, "Name doesn't match expected"
        assert act.props.color == self._AA_COLOR, "Color doesn't match expected"
        assert act.props.type == self._AA_TYPE, "Type doesn't match expected"
        assert act.props.joined == False, "Joined doesn't match expected"

        # Try to get activity by activity ID
        act2 = ps.get_activity(self._AA_ID)
        assert act2.props.id == self._AA_ID, "ID doesn't match expected"
        assert act2.props.name == self._AA_NAME, "Name doesn't match expected"
        assert act2.props.color == self._AA_COLOR, "Color doesn't match expected"
        assert act2.props.type == self._AA_TYPE, "Type doesn't match expected"
        assert act2.props.joined == False, "Joined doesn't match expected"

    def _testActivityDisappeared_helper_timeout(self, user_data):
        self._handle_error("Timeout waiting for activity-disappeared signal", user_data)
        return False

    def _testActivityDisappeared_helper_cb(self, ps, activity, user_data):
        user_data["activity"] = activity
        user_data["success"] = True
        gtk.main_quit()

    def _testActivityDisappeared_helper(self, user_data):
        busobj = dbus.SessionBus().get_object(mockps._PRESENCE_SERVICE,
                    mockps._PRESENCE_PATH)
        try:
            testps = dbus.Interface(busobj, mockps._PRESENCE_TEST_INTERFACE)
        except dbus.exceptions.DBusException, err:
            self._handle_error(err, user_data)
            return False

        # Add a fake activity
        try:
            testps.AddActivity(self._AA_ID, self._AA_NAME, self._AA_COLOR, self._AA_TYPE, {})
        except dbus.exceptions.DBusException, err:
            self._handle_error(err, user_data)
            return False

        ps = presenceservice.get_instance(False)
        ps.connect('activity-disappeared', self._testActivityDisappeared_helper_cb, user_data)
        # Wait 5 seconds max for signal to be emitted
        gobject.timeout_add(5000, self._testActivityDisappeared_helper_timeout, user_data)

        # Delete the fake activity
        try:
            testps.RemoveActivity(self._AA_ID)
        except dbus.exceptions.DBusException, err:
            self._handle_error(err, user_data)
            return False

        return False

    def testActivityDisappeared(self):
        ps = presenceservice.get_instance(False)
        assert ps, "Couldn't get presence service"

        user_data = {"success": False, "err": "", "activity": None}
        gobject.idle_add(self._testActivityDisappeared_helper, user_data)
        gtk.main()

        assert user_data["success"] == True, user_data["err"]
        assert user_data["activity"], "Activity was not received"

        act = user_data["activity"]
        assert act.props.id == self._AA_ID, "ID doesn't match expected"
        assert act.props.name == self._AA_NAME, "Name doesn't match expected"
        assert act.props.color == self._AA_COLOR, "Color doesn't match expected"
        assert act.props.type == self._AA_TYPE, "Type doesn't match expected"
        assert act.props.joined == False, "Joined doesn't match expected"

    def _testActivityShare_helper_is_done(self, user_data):
        if user_data["got-act-appeared"] and user_data["got-joined-activity"]:
            user_data["success"] = True
            gtk.main_quit()

    def _testActivityShare_helper_timeout(self, user_data):
        self._handle_error("Timeout waiting for activity share", user_data)
        return False

    def _testActivityShare_helper_joined_activity_cb(self, buddy, activity, user_data):
        user_data["joined-activity-buddy"] = buddy
        user_data["joined-activity-activity"] = activity
        user_data["got-joined-activity"] = True
        self._testActivityShare_helper_is_done(user_data)

    def _testActivityShare_helper_cb(self, ps, activity, user_data):
        user_data["activity"] = activity
        user_data["got-act-appeared"] = True
        self._testActivityShare_helper_is_done(user_data)

    def _testActivityShare_helper(self, user_data):
        ps = presenceservice.get_instance(False)
        mockact = MockSugarActivity(self._AA_ID, self._AA_NAME, self._AA_TYPE)

        ps.connect('activity-appeared', self._testActivityShare_helper_cb, user_data)
        try:
            # Hook up to the owner's joined-activity signal
            owner = ps.get_owner()
            owner.connect("joined-activity", self._testActivityShare_helper_joined_activity_cb, user_data)
        except RuntimeError, err:
            self._handle_error(err, user_data)
            return False

        # Wait 5 seconds max for signal to be emitted
        gobject.timeout_add(5000, self._testActivityShare_helper_timeout, user_data)

        ps.share_activity(mockact, self._AA_PROPS)

        return False

    def testActivityShare(self):
        ps = presenceservice.get_instance(False)
        assert ps, "Couldn't get presence service"

        user_data = {"success": False,
                     "err": "",
                     "activity": None,
                     "got-act-appeared": False,
                     "joined-activity-buddy": None,
                     "joined-activity-activity": None,
                     "got-joined-activity": False
                    }
        gobject.idle_add(self._testActivityShare_helper, user_data)
        gtk.main()

        assert user_data["success"] == True, user_data["err"]
        assert user_data["activity"], "Shared activity was not received"

        act = user_data["activity"]
        assert act.props.id == self._AA_ID, "ID doesn't match expected"
        assert act.props.name == self._AA_NAME, "Name doesn't match expected"
        # Shared activities from local machine take the owner's color
        assert act.props.color == mockps._OWNER_COLOR, "Color doesn't match expected"
        assert act.props.type == self._AA_TYPE, "Type doesn't match expected"
        assert act.props.joined == False, "Joined doesn't match expected"

        buddies = act.get_joined_buddies()
        assert len(buddies) == 1, "No buddies in activity"
        owner = buddies[0]
        assert owner.props.key == mockps._OWNER_PUBKEY, "Buddy key doesn't match expected"
        assert owner.props.nick == mockps._OWNER_NICK, "Buddy nick doesn't match expected"
        assert owner.props.color == mockps._OWNER_COLOR, "Buddy color doesn't match expected"

        real_owner = ps.get_owner()
        assert real_owner == owner, "Owner mismatch"

        assert user_data["joined-activity-activity"] == act, "Activity mismatch"
        assert user_data["joined-activity-buddy"] == owner, "Owner mismatch"

    def addToSuite(suite):
        suite.addTest(ActivityTests("testActivityAppeared"))
        suite.addTest(ActivityTests("testActivityDisappeared"))
        suite.addTest(ActivityTests("testActivityShare"))
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
