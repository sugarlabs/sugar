# Copyright (C) 2006-2007 Red Hat, Inc.
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

import logging

import gobject
import dbus
from telepathy.interfaces import CHANNEL, \
                                 CHANNEL_DISPATCHER, \
                                 CHANNEL_DISPATCH_OPERATION, \
                                 CHANNEL_TYPE_CONTACT_LIST, \
                                 CHANNEL_TYPE_DBUS_TUBE, \
                                 CHANNEL_TYPE_STREAMED_MEDIA, \
                                 CHANNEL_TYPE_STREAM_TUBE, \
                                 CHANNEL_TYPE_TEXT, \
                                 CLIENT

from jarabe.model import telepathyclient


class ActivityInvite(object):
    """Invitation to a shared activity."""
    def __init__(self, dispatch_operation_path, channel, handler):
        self._dispatch_operation_path = dispatch_operation_path
        self._channel = channel
        self._handler = handler

    def get_bundle_id(self):
        return self._handler[len(CLIENT + '.'):]

    def join(self):
        bus = dbus.Bus()
        obj = bus.get_object(CHANNEL_DISPATCHER, self._dispatch_operation_path)
        dispatch_operation = dbus.Interface(obj, CHANNEL_DISPATCH_OPERATION)
        dispatch_operation.HandleWith(self._handler,
                                      reply_handler=self.__handle_with_reply_cb,
                                      error_handler=self.__handle_with_reply_cb)

    def __handle_with_reply_cb(self, error=None):
        if error is not None:
            logging.error('__handle_with_reply_cb %r', error)
        else:
            logging.debug('__handle_with_reply_cb')


class Invites(gobject.GObject):
    __gsignals__ = {
        'invite-added':   (gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE, ([object])),
        'invite-removed': (gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE, ([object]))
    }

    def __init__(self):
        gobject.GObject.__init__(self)

        self._dispatch_operations = {}

        logging.info('KILL_PS listen for when the owner joins an activity')
        #ps = presenceservice.get_instance()
        #owner = ps.get_owner()
        #owner.connect('joined-activity', self._owner_joined_cb)

        client_handler = telepathyclient.get_instance()
        client_handler.got_dispatch_operation.connect(
                self.__got_dispatch_operation_cb)

    def __got_dispatch_operation_cb(self, **kwargs):
        logging.debug('__got_dispatch_operation_cb')
        dispatch_operation_path = kwargs['dispatch_operation_path']
        channel, channel_properties = kwargs['channels'][0]

        channel_type = channel_properties[CHANNEL + '.ChannelType']
        if channel_type == CHANNEL_TYPE_CONTACT_LIST:
            handler = None
            self._handle_with(dispatch_operation_path, CLIENT + '.Sugar')
        elif channel_type == CHANNEL_TYPE_TEXT:
            handler = CLIENT + '.org.laptop.Chat'
        elif channel_type == CHANNEL_TYPE_STREAMED_MEDIA:
            handler = CLIENT + '.org.laptop.VideoChat'
        elif channel_type == CHANNEL_TYPE_DBUS_TUBE:
            handler = channel_properties[CHANNEL_TYPE_DBUS_TUBE + '.ServiceName']
        elif channel_type == CHANNEL_TYPE_STREAM_TUBE:
            handler = channel_properties[CHANNEL_TYPE_STREAM_TUBE + '.Service']
        else:
            handler = None
            self._handle_with(dispatch_operation_path, '')

        if handler is not None:
            self._add_invite(dispatch_operation_path, channel, handler)

    def _handle_with(self, dispatch_operation_path, handler):
        logging.debug('_handle_with %r %r', dispatch_operation_path, handler)
        bus = dbus.Bus()
        obj = bus.get_object(CHANNEL_DISPATCHER, dispatch_operation_path)
        dispatch_operation = dbus.Interface(obj, CHANNEL_DISPATCH_OPERATION)
        dispatch_operation.HandleWith(handler,
                                      reply_handler=self.__handle_with_reply_cb,
                                      error_handler=self.__handle_with_reply_cb)

    def __handle_with_reply_cb(self, error=None):
        if error is not None:
            logging.error('__handle_with_reply_cb %r', error)
        else:
            logging.debug('__handle_with_reply_cb')

    def _add_invite(self, dispatch_operation_path, channel, handler):
        logging.debug('_add_invite %r %r %r', dispatch_operation_path, channel, handler)
        if dispatch_operation_path in self._dispatch_operations:
            # there is no point to have more than one invite for the same
            # dispatch operation
            return

        invite = ActivityInvite(dispatch_operation_path, channel, handler)
        self._dispatch_operations[dispatch_operation_path] = invite
        self.emit('invite-added', invite)

    def _remove_invite(self, invite):
        del self._dispatch_operations[invite.get_activity_id()]
        self.emit('invite-removed', invite)

    def remove_activity(self, activity_id):
        invite = self._dispatch_operations.get(activity_id)
        if invite is not None:
            self.remove_invite(invite)

    def remove_private_channel(self, private_channel):
        invite = self._dispatch_operations.get(private_channel)
        if invite is not None:
            self.remove_private_invite(invite)

    def _owner_joined_cb(self, owner, activity):
        self.remove_activity(activity.props.id)

    def __iter__(self):
        return self._dispatch_operations.values().__iter__()


_instance = None

def get_instance():
    global _instance
    if not _instance:
        _instance = Invites()
    return _instance
