# This should eventually land in telepathy-python, so has the same license:
# Copyright (C) 2008 Collabora Ltd. <http://www.collabora.co.uk/>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation; either version 2.1 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

# FIXME: this sould go upstream, in telepathy-python

import logging

import dbus
import dbus.mainloop.glib
from gi.repository import GObject

from telepathy.client import Connection
from telepathy.interfaces import CONN_INTERFACE
from telepathy.constants import CONNECTION_STATUS_CONNECTED, \
    CONNECTION_STATUS_DISCONNECTED


_instance = None


class ConnectionWatcher(GObject.GObject):
    __gsignals__ = {
        'connection-added': (GObject.SignalFlags.RUN_FIRST, None,
                             ([GObject.TYPE_PYOBJECT])),
        'connection-removed': (GObject.SignalFlags.RUN_FIRST, None,
                               ([GObject.TYPE_PYOBJECT])),
    }

    def __init__(self, bus=None):
        GObject.GObject.__init__(self)

        if bus is None:
            self.bus = dbus.Bus()
        else:
            self.bus = bus

        # D-Bus path -> Connection
        self._connections = {}

        self.bus.add_signal_receiver(self._status_changed_cb,
                                     dbus_interface=CONN_INTERFACE,
                                     signal_name='StatusChanged',
                                     path_keyword='path')

        for conn in Connection.get_connections(bus):
            conn.call_when_ready(self._conn_ready_cb)

    def _status_changed_cb(self, *args, **kwargs):
        path = kwargs['path']
        if not path.startswith('/org/freedesktop/Telepathy/Connection/'):
            return

        status, reason_ = args
        service_name = path.replace('/', '.')[1:]

        if status == CONNECTION_STATUS_CONNECTED:
            self._add_connection(service_name, path)
        elif status == CONNECTION_STATUS_DISCONNECTED:
            self._remove_connection(service_name, path)

    def _conn_ready_cb(self, conn):
        if conn.object_path in self._connections:
            return

        self._connections[conn.object_path] = conn
        self.emit('connection-added', conn)

    def _add_connection(self, service_name, path):
        if path in self._connections:
            return

        try:
            Connection(service_name, path, ready_handler=self._conn_ready_cb)
        except dbus.exceptions.DBusException:
            logging.debug('%s is propably already gone.', service_name)

    def _remove_connection(self, service_name, path):
        conn = self._connections.pop(path, None)
        if conn is None:
            return

        self.emit('connection-removed', conn)

    def get_connections(self):
        return self._connections.values()


def get_instance():
    global _instance
    if _instance is None:
        _instance = ConnectionWatcher()
    return _instance


if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    def connection_added_cb(conn_watcher, conn):
        print 'new connection', conn.service_name

    def connection_removed_cb(conn_watcher, conn):
        print 'removed connection', conn.service_name

    watcher = ConnectionWatcher()
    watcher.connect('connection-added', connection_added_cb)
    watcher.connect('connection-removed', connection_removed_cb)

    loop = GObject.MainLoop()
    loop.run()
