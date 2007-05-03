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

import os, time, sys
import dbus, dbus.glib
import gobject

from sugar.presence import presenceservice
from sugar.p2p import network

class ReadHTTPRequestHandler(network.ChunkedGlibHTTPRequestHandler):
    def translate_path(self, path):
        return self.server._filepath

class ReadHTTPServer(network.GlibTCPServer):
    def __init__(self, server_address, request_handler, filepath):
        self._filepath = filepath
        network.GlibTCPServer.__init__(self, server_address, request_handler);

class XMLRPCResponder(object):
    def __init__(self, have_file=False):
        self._have_file = have_file

    def _set_have_file(self):
        self._have_file = True

    def have_file(self):
        return self._have_file


class MockReadActivity(gobject.GObject):
    __gproperties__ = {
        'title'     : (str, None, None, None, gobject.PARAM_READABLE)
    }

    def __init__(self, filepath):
        self._actid = "ef60b3af42f7b5aa558ef9269e2ed7998798afc0"
        self._name = "Test Read Activity"
        self._type = "org.laptop.sugar.Xbook"
        gobject.GObject.__init__(self)

        self._ps_act = None
        self._filepath = os.path.abspath(filepath)
        self._file_server = ReadHTTPServer(("", 8867), ReadHTTPRequestHandler, self._filepath)

        self._xmlrpc_server = network.GlibXMLRPCServer(("", 8868))
        responder = XMLRPCResponder(have_file=True)
        self._xmlrpc_server.register_instance(responder)

    def _activity_appeared_cb(self, ps, activity):
        if activity.props.id != self._actid:
            return
        self._ps_act = activity

    def share(self):
        ps = presenceservice.get_instance()
        ps.connect("activity-appeared", self._activity_appeared_cb)
        ps.share_activity(self)
        return False

    def do_get_property(self, pspec):
        if pspec.name == "title":
            return self._name

    def get_id(self):
        return self._actid

    def get_service_name(self):
        return self._type

def start_ps():
    import commands
    (s, o) = commands.getstatusoutput("which sugar-presence-service")
    if s != 0:
        raise RuntimeError("Failed to find sugar presence service: %s" % o)
    argv = [o, "1"]
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

    print "Started presence service PID %d" % pid
    return pid


def stop_ps(pid):
    if pid >= 0:
        os.kill(pid, 15)
        print "Stopped presence service PID %d" % pid

def main():
    if len(sys.argv) != 2:
        raise RuntimeError("Must specify a PDF to share.")
    path = os.path.abspath(sys.argv[1])
    if not os.path.exists(path):
        raise RuntimeError("File %s doesn't exist." % path)
    mact = MockReadActivity(path)
    pid = start_ps()
    loop = gobject.MainLoop()
    gobject.timeout_add(2000, mact.share)
    try:
        loop.run()
    except KeyboardInterrupt:
        pass
    stop_ps(pid)

if __name__ == "__main__":
    main()
