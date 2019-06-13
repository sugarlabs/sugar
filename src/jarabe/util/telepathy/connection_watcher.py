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

from gi.repository import TelepathyGLib
CONN_INTERFACE = TelepathyGLib.IFACE_CONNECTION
CONNECTION_STATUS_CONNECTED = TelepathyGLib.ConnectionStatus.CONNECTED
CONNECTION_STATUS_DISCONNECTED = TelepathyGLib.ConnectionStatus.DISCONNECTED


_instance = None


class Connection():
    def __init__(self, service_name, object_path=None, bus=None,
            ready_handler=None):
        if not bus:
            self.bus = dbus.Bus()
        else:
            self.bus = bus

        self.service_name = service_name
        self.object_path = object_path
        self._ready_handlers = []
        if ready_handler is not None:
            self._ready_handlers.append(ready_handler)
        self._ready = False
        self._dbus_object = self.bus.get_object(service_name, object_path)
        self._interfaces = {}
        self._valid_interfaces = set()
        self._valid_interfaces.add(dbus.PROPERTIES_IFACE)
        self._valid_interfaces.add(CONN_INTERFACE)


        self._status_changed_connection = \
            self[CONN_INTERFACE].connect_to_signal('StatusChanged',
                lambda status, reason: self._status_cb(status))
        self[CONN_INTERFACE].GetStatus(
            reply_handler=self._status_cb,
            error_handler=self.default_error_handler)

    def _status_cb(self, status):
        if status == CONNECTION_STATUS_CONNECTED:
            self._get_interfaces()

            if self._status_changed_connection:
                self._status_changed_connection.remove()
                self._status_changed_connection = None

    def _get_interfaces(self):
        self[CONN_INTERFACE].GetInterfaces(
            reply_handler=self._get_interfaces_reply_cb,
            error_handler=self.default_error_handler)

    def _get_interfaces_reply_cb(self, interfaces):
        if self._ready:
            return

        self._ready = True

        self._valid_interfaces.update(interfaces)

        for ready_handler in self._ready_handlers:
            ready_handler(self)

    @staticmethod
    def get_connections(bus=None):
        connections = []
        if not bus:
            bus = dbus.Bus()

        bus_object = bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')

        for service in bus_object.ListNames(dbus_interface='org.freedesktop.DBus'):
            if service.startswith('org.freedesktop.Telepathy.Connection.'):
                connection = Connection(service, "/%s" % service.replace(".", "/"), bus)
                connections.append(connection)

        return connections

    def call_when_ready(self, handler):
        if self._ready:
            handler(self)
        else:
            self._ready_handlers.append(handler)

    def __getitem__(self, name):
        if name not in self._interfaces:
            if name not in self._valid_interfaces:
                raise KeyError(name)

            self._interfaces[name] = dbus.Interface(self._dbus_object, name)

        return self._interfaces[name]

    def __contains__(self, name):
        return name in self._interfaces or name in self._valid_interfaces

    def default_error_handler(exception):
        logging.debug('Exception from asynchronous method call:\n%s' % exception)


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
