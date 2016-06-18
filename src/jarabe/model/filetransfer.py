# Copyright (C) 2008 Tomeu Vizoso
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

import os
import logging
import socket

from gi.repository import GObject
from gi.repository import Gio
from gi.repository import GLib
import dbus
from telepathy.interfaces import \
    CONNECTION_INTERFACE_REQUESTS, \
    CHANNEL, \
    CHANNEL_DISPATCHER
from telepathy.constants import CONNECTION_HANDLE_TYPE_CONTACT,     \
    SOCKET_ADDRESS_TYPE_UNIX,           \
    SOCKET_ACCESS_CONTROL_LOCALHOST
from telepathy.client import Connection, Channel

from sugar3.presence import presenceservice
from sugar3 import dispatch

from jarabe.util.telepathy import connection_watcher
from jarabe.model import telepathyclient
from jarabe.model import neighborhood


FT_STATE_NONE = 0
FT_STATE_PENDING = 1
FT_STATE_ACCEPTED = 2
FT_STATE_OPEN = 3
FT_STATE_COMPLETED = 4
FT_STATE_CANCELLED = 5

FT_REASON_NONE = 0
FT_REASON_REQUESTED = 1
FT_REASON_LOCAL_STOPPED = 2
FT_REASON_REMOTE_STOPPED = 3
FT_REASON_LOCAL_ERROR = 4
FT_REASON_LOCAL_ERROR = 5
FT_REASON_REMOTE_ERROR = 6

# FIXME: use constants from tp-python once the spec is undrafted
CHANNEL_TYPE_FILE_TRANSFER = \
    'org.freedesktop.Telepathy.Channel.Type.FileTransfer'

new_file_transfer = dispatch.Signal()


class BaseFileTransfer(GObject.GObject):

    def __init__(self, connection):
        GObject.GObject.__init__(self)
        self._connection = connection
        self._state = FT_STATE_NONE
        self._transferred_bytes = 0

        self.channel = None
        self.buddy = None
        self.title = None
        self.file_size = None
        self.description = None
        self.mime_type = None
        self.initial_offset = 0
        self.reason_last_change = FT_REASON_NONE

    def set_channel(self, channel):
        self.channel = channel
        self.channel[CHANNEL_TYPE_FILE_TRANSFER].connect_to_signal(
            'FileTransferStateChanged', self.__state_changed_cb)
        self.channel[CHANNEL_TYPE_FILE_TRANSFER].connect_to_signal(
            'TransferredBytesChanged', self.__transferred_bytes_changed_cb)
        self.channel[CHANNEL_TYPE_FILE_TRANSFER].connect_to_signal(
            'InitialOffsetDefined', self.__initial_offset_defined_cb)

        channel_properties = self.channel[dbus.PROPERTIES_IFACE]

        props = channel_properties.GetAll(CHANNEL_TYPE_FILE_TRANSFER)
        self._state = props['State']
        self.title = props['Filename']
        self.file_size = props['Size']
        self.description = props['Description']
        self.mime_type = props['ContentType']

        handle = channel_properties.Get(CHANNEL, 'TargetHandle')
        self.buddy = neighborhood.get_model().get_buddy_by_handle(handle)

    def __transferred_bytes_changed_cb(self, transferred_bytes):
        logging.debug('__transferred_bytes_changed_cb %r', transferred_bytes)
        self.props.transferred_bytes = transferred_bytes

    def _set_transferred_bytes(self, transferred_bytes):
        self._transferred_bytes = transferred_bytes

    def _get_transferred_bytes(self):
        return self._transferred_bytes

    transferred_bytes = GObject.property(type=int,
                                         default=0,
                                         getter=_get_transferred_bytes,
                                         setter=_set_transferred_bytes)

    def __initial_offset_defined_cb(self, offset):
        logging.debug('__initial_offset_defined_cb %r', offset)
        self.initial_offset = offset

    def __state_changed_cb(self, state, reason):
        logging.debug('__state_changed_cb %r %r', state, reason)
        self.reason_last_change = reason
        self.props.state = state

    def _set_state(self, state):
        self._state = state

    def _get_state(self):
        return self._state

    state = GObject.property(type=int, getter=_get_state, setter=_set_state)

    def cancel(self):
        self.channel[CHANNEL].Close()


class IncomingFileTransfer(BaseFileTransfer):

    def __init__(self, connection, object_path, props):
        BaseFileTransfer.__init__(self, connection)

        channel = Channel(connection.service_name, object_path)
        self.set_channel(channel)

        self.connect('notify::state', self.__notify_state_cb)

        self.destination_path = None
        self._socket_address = None
        self._socket = None
        self._splicer = None

    def accept(self, destination_path):
        if os.path.exists(destination_path):
            raise ValueError('Destination path already exists: %r' %
                             destination_path)

        self.destination_path = destination_path

        channel_ft = self.channel[CHANNEL_TYPE_FILE_TRANSFER]
        self._socket_address = channel_ft.AcceptFile(
            SOCKET_ADDRESS_TYPE_UNIX,
            SOCKET_ACCESS_CONTROL_LOCALHOST,
            '',
            0,
            byte_arrays=True)

    def __notify_state_cb(self, file_transfer, pspec):
        logging.debug('__notify_state_cb %r', self.props.state)
        if self.props.state == FT_STATE_OPEN:
            # Need to hold a reference to the socket so that python doesn't
            # close the fd when it goes out of scope
            self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._socket.connect(self._socket_address)
            input_stream = Gio.UnixInputStream.new(self._socket.fileno(), True)

            destination_file = Gio.File.new_for_path(self.destination_path)
            if self.initial_offset == 0:
                output_stream = destination_file.create(
                    Gio.FileCreateFlags.PRIVATE, None)
            else:
                output_stream = destination_file.append_to()

            output_stream.splice_async(
                input_stream,
                Gio.OutputStreamSpliceFlags.CLOSE_SOURCE |
                Gio.OutputStreamSpliceFlags.CLOSE_TARGET,
                GLib.PRIORITY_LOW, None, None, None)


class OutgoingFileTransfer(BaseFileTransfer):

    def __init__(self, buddy, file_name, title, description, mime_type):

        presence_service = presenceservice.get_instance()
        name, path = presence_service.get_preferred_connection()
        connection = Connection(name, path,
                                ready_handler=self.__connection_ready_cb)

        BaseFileTransfer.__init__(self, connection)
        self.connect('notify::state', self.__notify_state_cb)

        self._file_name = file_name
        self._socket_address = None
        self._socket = None
        self._splicer = None
        self._output_stream = None

        self.buddy = buddy
        self.title = title
        self.file_size = os.stat(file_name).st_size
        self.description = description
        self.mime_type = mime_type

    def __connection_ready_cb(self, connection):
        requests = connection[CONNECTION_INTERFACE_REQUESTS]
        object_path, properties_ = requests.CreateChannel({
            CHANNEL + '.ChannelType': CHANNEL_TYPE_FILE_TRANSFER,
            CHANNEL + '.TargetHandleType': CONNECTION_HANDLE_TYPE_CONTACT,
            CHANNEL + '.TargetHandle': self.buddy.handle,
            CHANNEL_TYPE_FILE_TRANSFER + '.ContentType': self.mime_type,
            CHANNEL_TYPE_FILE_TRANSFER + '.Filename': self.title,
            CHANNEL_TYPE_FILE_TRANSFER + '.Size': self.file_size,
            CHANNEL_TYPE_FILE_TRANSFER + '.Description': self.description,
            CHANNEL_TYPE_FILE_TRANSFER + '.InitialOffset': 0})

        self.set_channel(Channel(connection.service_name, object_path))

        channel_file_transfer = self.channel[CHANNEL_TYPE_FILE_TRANSFER]
        self._socket_address = channel_file_transfer.ProvideFile(
            SOCKET_ADDRESS_TYPE_UNIX, SOCKET_ACCESS_CONTROL_LOCALHOST, '',
            byte_arrays=True)

    def __notify_state_cb(self, file_transfer, pspec):
        logging.debug('__notify_state_cb %r', self.props.state)
        if self.props.state == FT_STATE_OPEN:
            # Need to hold a reference to the socket so that python doesn't
            # closes the fd when it goes out of scope
            self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._socket.connect(self._socket_address)
            output_stream = Gio.UnixOutputStream.new(
                self._socket.fileno(), True)

            logging.debug('opening %s for reading', self._file_name)
            input_stream = Gio.File.new_for_path(self._file_name).read(None)
            if self.initial_offset > 0:
                input_stream.skip(self.initial_offset)

            output_stream.splice_async(
                input_stream,
                Gio.OutputStreamSpliceFlags.CLOSE_SOURCE |
                Gio.OutputStreamSpliceFlags.CLOSE_TARGET,
                GLib.PRIORITY_LOW, None, None, None)

    def cancel(self):
        self.channel[CHANNEL].Close()


def _new_channels_cb(connection, channels):
    for object_path, props in channels:
        if props[CHANNEL + '.ChannelType'] == CHANNEL_TYPE_FILE_TRANSFER and \
                not props[CHANNEL + '.Requested']:

            logging.debug('__new_channels_cb %r', object_path)

            incoming_file_transfer = IncomingFileTransfer(connection,
                                                          object_path, props)
            new_file_transfer.send(None, file_transfer=incoming_file_transfer)


def _monitor_connection(connection):
    logging.debug('connection added %r', connection)
    connection[CONNECTION_INTERFACE_REQUESTS].connect_to_signal(
        'NewChannels',
        lambda channels: _new_channels_cb(connection, channels))


def _connection_added_cb(conn_watcher, connection):
    _monitor_connection(connection)


def _connection_removed_cb(conn_watcher, connection):
    logging.debug('connection removed %r', connection)


def _got_dispatch_operation_cb(**kwargs):
    dispatch_operation_path = kwargs['dispatch_operation_path']
    channel_path, channel_properties = kwargs['channels'][0]
    channel_type = channel_properties[CHANNEL + '.ChannelType']
    handle_type = channel_properties[CHANNEL + '.TargetHandleType']

    if handle_type == CONNECTION_HANDLE_TYPE_CONTACT and \
       channel_type == CHANNEL_TYPE_FILE_TRANSFER:
        # We must claim our file transfers so that empathy doesn't get it
        bus = dbus.Bus()
        operation = bus.get_object(CHANNEL_DISPATCHER, dispatch_operation_path)
        operation.Claim()


def init():
    conn_watcher = connection_watcher.get_instance()
    conn_watcher.connect('connection-added', _connection_added_cb)
    conn_watcher.connect('connection-removed', _connection_removed_cb)

    for connection in conn_watcher.get_connections():
        _monitor_connection(connection)

    client_handler = telepathyclient.get_instance()
    client_handler.got_dispatch_operation.connect(_got_dispatch_operation_cb)


def start_transfer(buddy, file_name, title, description, mime_type):
    outgoing_file_transfer = OutgoingFileTransfer(buddy, file_name, title,
                                                  description, mime_type)
    new_file_transfer.send(None, file_transfer=outgoing_file_transfer)


def file_transfer_available():
    conn_watcher = connection_watcher.get_instance()
    for connection in conn_watcher.get_connections():

        try:
            properties_iface = connection[
                dbus.PROPERTIES_IFACE]
            properties = properties_iface.GetAll(
                CONNECTION_INTERFACE_REQUESTS)
        except dbus.DBusException as e:
            logging.exception(e)
            continue

        classes = properties['RequestableChannelClasses']
        for prop, allowed_prop in classes:

            channel_type = prop.get(CHANNEL + '.ChannelType', '')
            target_handle_type = prop.get(CHANNEL + '.TargetHandleType', '')

            if len(prop) == 2 and \
                    channel_type == CHANNEL_TYPE_FILE_TRANSFER and \
                    target_handle_type == CONNECTION_HANDLE_TYPE_CONTACT:
                return True

        return False


if __name__ == '__main__':
    import tempfile

    test_file_name = '/home/humitos/test.py'
    test_temp_file = tempfile.mkstemp()[1]
    print test_temp_file
    test_input_stream = Gio.File.new_for_path(test_file_name).read(None)
    test_output_stream = Gio.File.new_for_path(test_temp_file)\
        .append_to(Gio.FileCreateFlags.PRIVATE, None)

    test_output_stream.splice_async(
        test_input_stream,
        Gio.OutputStreamSpliceFlags.CLOSE_SOURCE |
        Gio.OutputStreamSpliceFlags.CLOSE_TARGET,
        GLib.PRIORITY_LOW, None, None, None)

    loop = GObject.MainLoop()
    loop.run()
