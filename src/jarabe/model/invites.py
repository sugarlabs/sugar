# Copyright (C) 2006-2007 Red Hat, Inc.
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
from functools import partial
import json

from gi.repository import GObject
import dbus
from telepathy.interfaces import CHANNEL, \
    CHANNEL_DISPATCHER, \
    CHANNEL_DISPATCH_OPERATION, \
    CHANNEL_TYPE_CONTACT_LIST, \
    CHANNEL_TYPE_TEXT, \
    CLIENT
from telepathy.constants import HANDLE_TYPE_ROOM

from sugar3.graphics.xocolor import XoColor
from sugar3 import profile

from jarabe.model import telepathyclient
from jarabe.model import bundleregistry
from jarabe.model import neighborhood
from jarabe.journal import misc


CONNECTION_INTERFACE_ACTIVITY_PROPERTIES = \
    'org.laptop.Telepathy.ActivityProperties'

_instance = None


class BaseInvite(object):
    """Invitation to shared activity or private 1-1 Telepathy channel"""

    def __init__(self, dispatch_operation_path, handle, handler):
        self.dispatch_operation_path = dispatch_operation_path
        self._handle = handle
        self._handler = handler

    def get_bundle_id(self):
        if CLIENT in self._handler:
            return self._handler[len(CLIENT + '.'):]
        else:
            return None

    def get_activity_title(self):
        return None

    def _call_handle_with(self):
        bus = dbus.Bus()
        obj = bus.get_object(CHANNEL_DISPATCHER, self.dispatch_operation_path)
        dispatch_operation = dbus.Interface(obj, CHANNEL_DISPATCH_OPERATION)
        dispatch_operation.HandleWith(self._handler,
                                      reply_handler=self._handle_with_reply_cb,
                                      error_handler=self._handle_with_reply_cb)

    def _handle_with_reply_cb(self, error=None):
        if error is not None:
            raise error
        else:
            logging.debug('_handle_with_reply_cb')

    def _name_owner_changed_cb(self, name, old_owner, new_owner):
        logging.debug('BaseInvite._name_owner_changed_cb %r %r %r', name,
                      new_owner, old_owner)
        if name == self._handler and new_owner and not old_owner:
            self._call_handle_with()


class ActivityInvite(BaseInvite):
    """Invitation to a shared activity."""

    def __init__(self, dispatch_operation_path, handle, handler,
                 activity_properties):
        BaseInvite.__init__(self, dispatch_operation_path, handle, handler)

        if activity_properties is not None:
            self._activity_properties = activity_properties
        else:
            self._activity_properties = {}

    def get_color(self):
        color = self._activity_properties.get('color', None)
        # arrives unicode but we connect with byte_arrays=True - SL #4157
        if color is not None:
            color = str(color)
        return XoColor(color)

    def get_activity_title(self):
        return self._activity_properties.get('name')

    def join(self):
        logging.error('ActivityInvite.join handler %r', self._handler)

        registry = bundleregistry.get_registry()
        bundle_id = self.get_bundle_id()
        bundle = registry.get_bundle(bundle_id)
        if bundle is None:
            self._call_handle_with()
            return

        bus = dbus.SessionBus()
        bus.add_signal_receiver(self._name_owner_changed_cb,
                                'NameOwnerChanged',
                                'org.freedesktop.DBus',
                                arg0=self._handler)

        model = neighborhood.get_model()
        activity_id = model.get_activity_by_room(self._handle).activity_id
        misc.launch(bundle, color=self.get_color(), invited=True,
                    activity_id=activity_id)


class PrivateInvite(BaseInvite):

    def __init__(self, dispatch_operation_path, handle, handler,
                 private_channel):
        BaseInvite.__init__(self, dispatch_operation_path, handle, handler)

        self._private_channel = private_channel

    def get_color(self):
        return profile.get_color()

    def join(self):
        logging.error('PrivateInvite.join handler %r', self._handler)
        registry = bundleregistry.get_registry()
        bundle_id = self.get_bundle_id()
        bundle = registry.get_bundle(bundle_id)

        bus = dbus.SessionBus()
        bus.add_signal_receiver(self._name_owner_changed_cb,
                                'NameOwnerChanged',
                                'org.freedesktop.DBus',
                                arg0=self._handler)
        misc.launch(bundle, color=self.get_color(), invited=True,
                    uri=self._private_channel)


class Invites(GObject.GObject):
    __gsignals__ = {
        'invite-added': (GObject.SignalFlags.RUN_FIRST, None,
                         ([object])),
        'invite-removed': (GObject.SignalFlags.RUN_FIRST, None,
                           ([object])),
    }

    def __init__(self):
        GObject.GObject.__init__(self)

        self._dispatch_operations = {}

        client_handler = telepathyclient.get_instance()
        client_handler.got_dispatch_operation.connect(
            self.__got_dispatch_operation_cb)

    def __got_dispatch_operation_cb(self, **kwargs):
        logging.debug('__got_dispatch_operation_cb')
        dispatch_operation_path = kwargs['dispatch_operation_path']
        channel_path, channel_properties = kwargs['channels'][0]
        properties = kwargs['properties']
        channel_type = channel_properties[CHANNEL + '.ChannelType']
        handle_type = channel_properties[CHANNEL + '.TargetHandleType']
        handle = channel_properties[CHANNEL + '.TargetHandle']

        if handle_type == HANDLE_TYPE_ROOM and \
           channel_type == CHANNEL_TYPE_TEXT:
            logging.debug('May be an activity, checking its properties')
            connection_path = properties[CHANNEL_DISPATCH_OPERATION +
                                         '.Connection']
            connection_name = connection_path.replace('/', '.')[1:]

            bus = dbus.Bus()
            connection = bus.get_object(connection_name, connection_path)
            connection.GetProperties(
                channel_properties[CHANNEL + '.TargetHandle'],
                dbus_interface=CONNECTION_INTERFACE_ACTIVITY_PROPERTIES,
                reply_handler=partial(self.__get_properties_cb,
                                      handle,
                                      dispatch_operation_path),
                error_handler=partial(self.__error_handler_cb,
                                      handle,
                                      channel_properties,
                                      dispatch_operation_path,
                                      channel_path,
                                      properties))
        else:
            self._dispatch_non_sugar_invitation(handle,
                                                channel_properties,
                                                dispatch_operation_path,
                                                channel_path,
                                                properties)

    def __get_properties_cb(self, handle, dispatch_operation_path, properties):
        logging.debug('__get_properties_cb %r', properties)
        handler = '%s.%s' % (CLIENT, properties['type'])
        self._add_invite(dispatch_operation_path, handle, handler, properties)

    def __error_handler_cb(self, handle, channel_properties,
                           dispatch_operation_path, channel_path,
                           properties, error):
        logging.debug('__error_handler_cb %r', error)
        exception_name = 'org.freedesktop.Telepathy.Error.NotAvailable'
        if error.get_dbus_name() == exception_name:
            self._dispatch_non_sugar_invitation(handle,
                                                channel_properties,
                                                dispatch_operation_path,
                                                channel_path,
                                                properties)
        else:
            raise error

    def _dispatch_non_sugar_invitation(self, handle, channel_properties,
                                       dispatch_operation_path, channel_path,
                                       properties):
        handler = None
        channel_type = channel_properties[CHANNEL + '.ChannelType']
        if channel_type == CHANNEL_TYPE_CONTACT_LIST:
            self._handle_with(dispatch_operation_path, CLIENT + '.Sugar')
        elif channel_type == CHANNEL_TYPE_TEXT:
            handler = CLIENT + '.org.laptop.Chat'
            self._add_private_invite(dispatch_operation_path, handle, handler,
                                     channel_path, properties)
            return
        else:
            self._call_handle_with(dispatch_operation_path, '')

        if handler is not None:
            logging.debug('Adding an invite from a non-Sugar client')
            self._add_invite(dispatch_operation_path, handle, handler)

    def _call_handle_with(self, dispatch_operation_path, handler):
        logging.debug('_handle_with %r %r', dispatch_operation_path, handler)
        bus = dbus.Bus()
        obj = bus.get_object(CHANNEL_DISPATCHER, dispatch_operation_path)
        dispatch_operation = dbus.Interface(obj, CHANNEL_DISPATCH_OPERATION)
        dispatch_operation.HandleWith(
            handler,
            reply_handler=self.__handle_with_reply_cb,
            error_handler=self.__handle_with_reply_cb)

    def __handle_with_reply_cb(self, error=None):
        if error is not None:
            logging.error('__handle_with_reply_cb %r', error)
        else:
            logging.debug('__handle_with_reply_cb')

    def _add_invite(self, dispatch_operation_path, handle, handler,
                    activity_properties=None):
        logging.debug('_add_invite %r %r %r', dispatch_operation_path, handle,
                      handler)
        if dispatch_operation_path in self._dispatch_operations:
            # there is no point to have more than one invite for the same
            # dispatch operation
            return

        invite = ActivityInvite(dispatch_operation_path, handle, handler,
                                activity_properties)
        self._dispatch_operations[dispatch_operation_path] = invite
        self.emit('invite-added', invite)

    def _add_private_invite(self, dispatch_operation_path, handle, handler,
                            channel_path, properties):
        connection_path = properties[CHANNEL_DISPATCH_OPERATION +
                                     '.Connection']
        connection_name = connection_path.replace('/', '.')[1:]
        private_channel = json.dumps([connection_name,
                                      connection_path, channel_path])
        invite = PrivateInvite(dispatch_operation_path, handle, handler,
                               private_channel)
        self._dispatch_operations[dispatch_operation_path] = invite
        self.emit('invite-added', invite)

    def remove_invite(self, invite):
        del self._dispatch_operations[invite.dispatch_operation_path]
        self.emit('invite-removed', invite)

    def __iter__(self):
        return self._dispatch_operations.values().__iter__()


def get_instance():
    global _instance
    if not _instance:
        _instance = Invites()
    return _instance
