# This should eventually land in telepathy-python, so has the same license:

# Copyright (C) 2007 Collabora Ltd. <http://www.collabora.co.uk/>
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


__all__ = ('TubeConnection',)
__docformat__ = 'reStructuredText'


import logging

from dbus.connection import Connection


logger = logging.getLogger('telepathy.tubeconn')


class TubeConnection(Connection):

    def __new__(cls, conn, tubes_iface, tube_id, address=None,
                group_iface=None, mainloop=None):
        if address is None:
            address = tubes_iface.GetDBusTubeAddress(tube_id)
        self = super(TubeConnection, cls).__new__(cls, address,
                                                  mainloop=mainloop)

        self._tubes_iface = tubes_iface
        self.tube_id = tube_id
        self.participants = {}
        self.bus_name_to_handle = {}
        self._mapping_watches = []

        if group_iface is None:
            method = conn.GetSelfHandle
        else:
            method = group_iface.GetSelfHandle
        method(reply_handler=self._on_get_self_handle_reply,
               error_handler=self._on_get_self_handle_error)

        return self

    def _on_get_self_handle_reply(self, handle):
        self.self_handle = handle
        match = self._tubes_iface.connect_to_signal('DBusNamesChanged',
                self._on_dbus_names_changed)
        self._tubes_iface.GetDBusNames(self.tube_id,
                reply_handler=self._on_get_dbus_names_reply,
                error_handler=self._on_get_dbus_names_error)
        self._dbus_names_changed_match = match

    def _on_get_self_handle_error(self, e):
        logging.basicConfig()
        logger.error('GetSelfHandle failed: %s', e)

    def close(self):
        self._dbus_names_changed_match.remove()
        self._on_dbus_names_changed(self.tube_id, (), self.participants.keys())
        super(TubeConnection, self).close()

    def _on_get_dbus_names_reply(self, names):
        self._on_dbus_names_changed(self.tube_id, names, ())

    def _on_get_dbus_names_error(self, e):
        logging.basicConfig()
        logger.error('GetDBusNames failed: %s', e)

    def _on_dbus_names_changed(self, tube_id, added, removed):
        if tube_id == self.tube_id:
            for handle, bus_name in added:
                if handle == self.self_handle:
                    # I've just joined - set my unique name
                    self.set_unique_name(bus_name)
                self.participants[handle] = bus_name
                self.bus_name_to_handle[bus_name] = handle

            # call the callback while the removed people are still in
            # participants, so their bus names are available
            for callback in self._mapping_watches:
                callback(added, removed)

            for handle in removed:
                bus_name = self.participants.pop(handle, None)
                self.bus_name_to_handle.pop(bus_name, None)

    def watch_participants(self, callback):
        self._mapping_watches.append(callback)
        if self.participants:
            # GetDBusNames already returned: fake a participant add event
            # immediately
            added = []
            for k, v in self.participants.iteritems():
                added.append((k, v))
            callback(added, [])
