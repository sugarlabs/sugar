# Copyright (C) 2010 Collabora Ltd. <http://www.collabora.co.uk/>
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

import logging

import dbus
from dbus import PROPERTIES_IFACE
from telepathy.interfaces import CLIENT, \
    CHANNEL, \
    CHANNEL_TYPE_TEXT, \
    CHANNEL_TYPE_FILE_TRANSFER, \
    CLIENT_APPROVER, \
    CLIENT_HANDLER, \
    CLIENT_INTERFACE_REQUESTS
from telepathy.server import DBusProperties

from telepathy.constants import CONNECTION_HANDLE_TYPE_ROOM
from telepathy.constants import CONNECTION_HANDLE_TYPE_CONTACT

from sugar3 import dispatch


SUGAR_CLIENT_SERVICE = 'org.freedesktop.Telepathy.Client.Sugar'
SUGAR_CLIENT_PATH = '/org/freedesktop/Telepathy/Client/Sugar'

_instance = None


class TelepathyClient(dbus.service.Object, DBusProperties):

    def __init__(self):
        self._interfaces = set([CLIENT, CLIENT_HANDLER,
                                CLIENT_INTERFACE_REQUESTS, PROPERTIES_IFACE,
                                CLIENT_APPROVER])

        bus = dbus.Bus()
        bus_name = dbus.service.BusName(SUGAR_CLIENT_SERVICE, bus=bus)

        dbus.service.Object.__init__(self, bus_name, SUGAR_CLIENT_PATH)
        DBusProperties.__init__(self)

        self._implement_property_get(CLIENT, {
            'Interfaces': lambda: list(self._interfaces),
        })
        self._implement_property_get(CLIENT_HANDLER, {
            'HandlerChannelFilter': self.__get_filters_handler_cb,
        })
        self._implement_property_get(CLIENT_APPROVER, {
            'ApproverChannelFilter': self.__get_filters_approver_cb,
        })

        self.got_channel = dispatch.Signal()
        self.got_dispatch_operation = dispatch.Signal()

    def __get_filters_handler_cb(self):
        filter_dict = dbus.Dictionary({}, signature='sv')
        return dbus.Array([filter_dict], signature='a{sv}')

    def __get_filters_approver_cb(self):
        activity_invitation = {
            CHANNEL + '.ChannelType': CHANNEL_TYPE_TEXT,
            CHANNEL + '.TargetHandleType': CONNECTION_HANDLE_TYPE_ROOM,
        }
        filter_dict = dbus.Dictionary(activity_invitation, signature='sv')
        filters = dbus.Array([filter_dict], signature='a{sv}')

        text_invitation = {
            CHANNEL + '.ChannelType': CHANNEL_TYPE_TEXT,
            CHANNEL + '.TargetHandleType': CONNECTION_HANDLE_TYPE_CONTACT,
        }
        filter_dict = dbus.Dictionary(text_invitation, signature='sv')
        filters.append(filter_dict)

        ft_invitation = {
            CHANNEL + '.ChannelType': CHANNEL_TYPE_FILE_TRANSFER,
            CHANNEL + '.TargetHandleType': CONNECTION_HANDLE_TYPE_CONTACT,
        }
        filter_dict = dbus.Dictionary(ft_invitation, signature='sv')
        filters.append(filter_dict)

        logging.debug('__get_filters_approver_cb %r', filters)
        return filters

    @dbus.service.method(dbus_interface=CLIENT_HANDLER,
                         in_signature='ooa(oa{sv})aota{sv}', out_signature='')
    def HandleChannels(self, account, connection, channels, requests_satisfied,
                       user_action_time, handler_info):
        logging.debug('HandleChannels\n%r\n%r\n%r\n%r\n%r\n%r\n', account,
                      connection, channels, requests_satisfied,
                      user_action_time, handler_info)
        for channel in channels:
            self.got_channel.send(self, account=account,
                                  connection=connection, channel=channel)

    @dbus.service.method(dbus_interface=CLIENT_INTERFACE_REQUESTS,
                         in_signature='oa{sv}', out_signature='')
    def AddRequest(self, request, properties):
        logging.debug('AddRequest\n%r\n%r', request, properties)

    @dbus.service.method(dbus_interface=CLIENT_APPROVER,
                         in_signature='a(oa{sv})oa{sv}', out_signature='',
                         async_callbacks=('success_cb', 'error_cb_'))
    def AddDispatchOperation(self, channels, dispatch_operation_path,
                             properties, success_cb, error_cb_):
        success_cb()
        try:
            logging.debug('AddDispatchOperation\n%r\n%r\n%r', channels,
                          dispatch_operation_path, properties)

            self.got_dispatch_operation.send(
                self,
                channels=channels,
                dispatch_operation_path=dispatch_operation_path,
                properties=properties)
        except Exception as e:
            logging.exception(e)


def get_instance():
    global _instance
    if not _instance:
        _instance = TelepathyClient()
    return _instance
