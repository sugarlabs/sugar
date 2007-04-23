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
    if pid >= 0:
        os.kill(pid, 15)
    

class BuddyTests(unittest.TestCase):
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

        user_data = {"success": False, "err": "", "buddy": None, "ps": ps}
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

    def addToSuite(suite):
        suite.addTest(BuddyTests("testOwner"))
        suite.addTest(BuddyTests("testBuddyAppeared"))
    addToSuite = staticmethod(addToSuite)

def main():
    suite = unittest.TestSuite()
    BuddyTests.addToSuite(suite)
    runner = unittest.TextTestRunner()
    runner.run(suite)

if __name__ == "__main__":
    main()
