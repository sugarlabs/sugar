# Copyright (C) 2008 One Laptop Per Child
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

import sys
import logging

import dbus

from sugar3 import dispatch

from jarabe import config


_DBUS_SERVICE = 'org.freedesktop.Notifications'
_DBUS_IFACE = 'org.freedesktop.Notifications'
_DBUS_PATH = '/org/freedesktop/Notifications'

_instance = None


class NotificationService(dbus.service.Object):

    def __init__(self):
        bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(_DBUS_SERVICE, bus=bus)
        dbus.service.Object.__init__(self, bus_name, _DBUS_PATH)

        self._notification_counter = 0
        self.notification_received = dispatch.Signal()
        self.notification_cancelled = dispatch.Signal()

        self._buffer = {}
        self.buffer_cleared = dispatch.Signal()

    def retrieve_by_name(self, name):
        if name in self._buffer:
            return self._buffer[name]
        return None

    def clear_by_name(self, name):
        if name in self._buffer:
            del self._buffer[name]
        self.buffer_cleared.send(self, app_name=name)

    @dbus.service.method(_DBUS_IFACE,
                         in_signature='susssava{sv}i', out_signature='u')
    def Notify(self, app_name, replaces_id, app_icon, summary, body, actions,
               hints, expire_timeout):

        logging.debug('Received notification: %r',
                      [app_name, replaces_id,
                       '<app_icon>', summary, body, actions, '<hints>',
                       expire_timeout])

        if replaces_id > 0:
            notification_id = replaces_id
        else:
            if self._notification_counter == sys.maxsize:
                self._notification_counter = 1
            else:
                self._notification_counter += 1
            notification_id = self._notification_counter

        if app_name not in self._buffer:
            self._buffer[app_name] = []
        self._buffer[app_name].append({'app_name': app_name,
                                       'replaces_id': replaces_id,
                                       'app_icon': app_icon,
                                       'summary': summary,
                                       'body': body,
                                       'actions': actions,
                                       'hints': hints,
                                       'expire_timeout': expire_timeout})

        self.notification_received.send(self,
                                        app_name=app_name,
                                        replaces_id=replaces_id,
                                        app_icon=app_icon,
                                        summary=summary,
                                        body=body,
                                        actions=actions,
                                        hints=hints,
                                        expire_timeout=expire_timeout)

        return notification_id

    @dbus.service.method(_DBUS_IFACE, in_signature='u', out_signature='')
    def CloseNotification(self, notification_id):
        self.notification_cancelled.send(self, notification_id=notification_id)

    @dbus.service.method(_DBUS_IFACE, in_signature='', out_signature='as')
    def GetCapabilities(self):
        return []

    @dbus.service.method(_DBUS_IFACE, in_signature='', out_signature='sss')
    def GetServerInformation(self, name, vendor, version):
        return 'Sugar Shell', 'Sugar', config.version

    @dbus.service.signal(_DBUS_IFACE, signature='uu')
    def NotificationClosed(self, notification_id, reason):
        pass

    @dbus.service.signal(_DBUS_IFACE, signature='us')
    def ActionInvoked(self, notification_id, action_key):
        pass


def get_service():
    global _instance
    if not _instance:
        _instance = NotificationService()
    return _instance


def init():
    get_service()
