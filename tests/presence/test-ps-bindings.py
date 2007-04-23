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

class PSBindingsTestCase(unittest.TestCase):
    def setUp(self):
        argv = ["mockps.py", "mockps.py"]
        (self._pspid, stdin, stdout, stderr) = gobject.spawn_async(argv, flags=gobject.SPAWN_LEAVE_DESCRIPTORS_OPEN)
        print "Presence service started, pid %d" % self._pspid

        # Wait until it shows up on the bus
        tries = 0
        bus = dbus.SessionBus()
        while tries < 5:
            bus_object = bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
            try:
                if bus_object.GetNameOwner(presenceservice.DBUS_SERVICE, dbus_interface='org.freedesktop.DBus'):
                    break
            except dbus.exceptions.DBusException, err:
                pass
            time.sleep(1)
            tries += 1

        if tries >= 5:
            self.tearDown()
            raise RuntimeError("Couldn't start the mock presence service")

    def tearDown(self):
        if self._pspid >= 0:
            os.kill(self._pspid, 15)
        self._pspid = -1
        print "Presence service stopped."

    def _handle_error(self, err, user_data):
        user_data["success"] = False
        user_data["err"] = str(err)
        gtk.main_quit()

    def _testOwner_helper(self, user_data):
        try:
            ps = presenceservice.PresenceService(False)
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

    def addToSuite(suite):
        suite.addTest(PSBindingsTestCase("testOwner"))
    addToSuite = staticmethod(addToSuite)

def main():
    suite = unittest.TestSuite()
    PSBindingsTestCase.addToSuite(suite)
    runner = unittest.TextTestRunner()
    runner.run(suite)

if __name__ == "__main__":
    main()
