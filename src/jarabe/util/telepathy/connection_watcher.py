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
from functools import partial

import dbus
from dbus import PROPERTIES_IFACE
import dbus.mainloop.glib
from gi.repository import GObject

from gi.repository import TelepathyGLib
CONN_INTERFACE = TelepathyGLib.IFACE_CONNECTION
CONNECTION_INTERFACE_REQUESTS = \
    TelepathyGLib.IFACE_CONNECTION_INTERFACE_REQUESTS

CONNECTION_STATUS_CONNECTED = TelepathyGLib.ConnectionStatus.CONNECTED
CONNECTION_STATUS_DISCONNECTED = TelepathyGLib.ConnectionStatus.DISCONNECTED


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

        bus_object = self.bus.get_object(
            'org.freedesktop.DBus', '/org/freedesktop/DBus')
        bus_object.ListNames(
            dbus_interface='org.freedesktop.DBus',
            reply_handler=self.__get_services_reply_cb,
            error_handler=self.__error_handler_cb)

    def __get_services_reply_cb(self, services):
        for service in services:
            if service.startswith('org.freedesktop.Telepathy.Connection.'):
                object_path = "/%s" % service.replace(".", "/")
                conn_proxy = self.bus.get_object(service, object_path)
                self._prepare_conn_cb(object_path, conn_proxy)

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

    def _prepare_conn_cb(self, object_path, conn_proxy):
        connection = {}
        connection["service_name"] = object_path.replace('/', '.')[1:]
        connection[PROPERTIES_IFACE] = dbus.Interface(
            conn_proxy, PROPERTIES_IFACE)
        connection[CONNECTION_INTERFACE_REQUESTS] = \
            dbus.Interface(conn_proxy, CONNECTION_INTERFACE_REQUESTS)
        connection[CONN_INTERFACE] = \
            dbus.Interface(conn_proxy, CONN_INTERFACE)
        connection[CONN_INTERFACE].GetInterfaces(
            reply_handler=partial(self.__conn_get_interfaces_reply_cb,
                                  object_path, conn_proxy, connection),
            error_handler=self.__error_handler_cb)

    def __conn_get_interfaces_reply_cb(self, object_path, conn_proxy,
                                       connection, interfaces):
        for interface in interfaces:
            connection[interface] = dbus.Interface(conn_proxy, interface)

        if object_path in self._connections:
            return

        self._connections[object_path] = connection
        self.emit('connection-added', connection)

    def _add_connection(self, service_name, path):
        if path in self._connections:
            return

        try:
            conn_proxy = dbus.Bus().get_object(service_name, path)
            self._prepare_conn_cb(path, conn_proxy)
        except dbus.exceptions.DBusException:
            logging.debug('%s is propably already gone.', service_name)

    def _remove_connection(self, service_name, path):
        conn = self._connections.pop(path, None)
        if conn is None:
            return

        self.emit('connection-removed', conn)

    def get_connections(self):
        return list(self._connections.values())

    def __error_handler_cb(exception):
        logging.debug(
            'Exception from asynchronous method call:\n%s' % exception)


def get_instance():
    global _instance
    if _instance is None:
        _instance = ConnectionWatcher()
    return _instance


if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    def connection_added_cb(conn_watcher, conn):
        print('new connection', conn["service_name"])

    def connection_removed_cb(conn_watcher, conn):
        print('removed connection', conn["service_name"])

    watcher = ConnectionWatcher()
    watcher.connect('connection-added', connection_added_cb)
    watcher.connect('connection-removed', connection_removed_cb)

    loop = GObject.MainLoop()
    loop.run()
