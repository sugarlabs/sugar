# Copyright (C) 2016, Abhijit Patel 
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
	
import os
import json
import socket
import logging
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gio
from gi.repository import GLib
import dbus

from telepathy.interfaces import \
    CHANNEL_INTERFACE, \
    CHANNEL_INTERFACE_GROUP, \
    CHANNEL_TYPE_TEXT, \
    CHANNEL_TYPE_FILE_TRANSFER, \
    CONN_INTERFACE_ALIASING, \
    CONNECTION_INTERFACE_REQUESTS, \
    CHANNEL, \
    CLIENT
from telepathy.constants import \
    CHANNEL_GROUP_FLAG_CHANNEL_SPECIFIC_HANDLES, \
    CONNECTION_HANDLE_TYPE_CONTACT, \
    CHANNEL_TEXT_MESSAGE_TYPE_NORMAL, \
    CONNECTION_HANDLE_TYPE_CONTACT, \
    SOCKET_ADDRESS_TYPE_UNIX, \
    SOCKET_ACCESS_CONTROL_LOCALHOST
from telepathy.client import Connection, Channel

from sugar3.graphics.icon import Icon
from sugar3.presence import presenceservice
from sugar3.activity.activity import SCOPE_PRIVATE
from sugar3.graphics.alert import NotifyAlert, Alert

from jarabe.journal import journalwindow

ACTION_INIT_REQUEST = '!!ACTION_INIT_REQUEST'
ACTION_INIT_RESPONSE = '!!ACTION_INIT_RESPONSE'
ACTIVITY_FT_MIME = 'x-sugar/from-activity'

class ProjectWrapper(GObject.GObject):

    message = GObject.Signal('message', arg_types=[object, object])
    joined = GObject.Signal('joined')
    buddy_joined = GObject.Signal('buddy_joined', arg_types=[object])
    buddy_left = GObject.Signal('buddy_left', arg_types=[object])

    def __init__(self, project):
        GObject.GObject.__init__(self)
        self.project = project
        self.shared_project = project.shared_activity
        self._leader = False
        self._init_waiting = False
        self._text_channel = None

    def _show_alert(self, title):
        alert = Alert()
        alert.props.title = title
        icon = Icon(icon_name='dialog-cancel')
        alert.add_button(Gtk.ResponseType.CANCEL, _('Cancel'), icon)
        icon.show()

        alert.connect('response', self._alert_response_cb, entry)
        journalwindow.get_journal_window().add_alert(alert)
        alert.show()

    def setup(self):
        if self.shared_project:
	    self.project.connect("joined", self.__joined_cb)

            if self.project.get_shared():
	        logging.debug('calling __joined_cb')
		self.__joined_cb(self)
            else:
                logging.debug('Joining project')
                self._show_alert('Joining project')			

        else:
            self._leader = True
            self.project.connect('shared', self.__shared_cb)

    def _alert_response_cb(self, alert, response_id, entry):
        journalwindow.get_journal_window().remove_alert(alert)

    def __shared_cb(self, sender):
        logging.debug('ProjectWrapper.__shared_cb')
        self.shared_project = self.project.shared_activity
        self._setup_text_channel()
        self._listen_for_channels()

    def __joined_cb(self, sender):
        self.shared_project = self.project.shared_activity
        if not self.shared_project:
            self._show_alert('No shared activity cant join')
            return

        self._setup_text_channel()
        self._listen_for_channels()
        self._init_waiting = True
        self._show_alert('I joined a shared activity.')
        self.post({'action': ACTION_INIT_REQUEST})

    def _setup_text_channel(self):
        self._text_channel = _TextChannelWrapper(
            self.shared_project.telepathy_text_chan,
            self.shared_project.telepathy_conn)

        self._text_channel.set_received_callback(self.__received_cb)
        self.shared_project.connect('buddy-joined', self.__buddy_joined_cb)
        self.shared_project.connect('buddy-left', self.__buddy_left_cb)

    def _listen_for_channels(self):
        conn = self.shared_project.telepathy_conn
        conn.connect_to_signal('NewChannels', self.__new_channels_cb)

    def __new_channels_cb(self, channels):
        conn = self.shared_project.telepathy_conn
        for path, props in channels:
            if props[CHANNEL + '.Requested']:
                #channel reuquested by me
                continue

            channel_type = props[CHANNEL + '.ChannelType']
            if channel_type == CHANNEL_TYPE_FILE_TRANSFER:
                return #no file transfer yet implemented!

    def __received_cb(self, buddy, msg):
        action = msg.get('action')
        if action == ACTION_INIT_REQUEST and self._leader:
            data = {"answer": [42.2], "abs": 42}
            data = json.dumps(data)
            OutgoingBlobTransfer(
                buddy,
                self.shared_project.telepathy_conn,
                data,
                self.get_client_name(),
                ACTION_INIT_RESPONSE,
                ACTIVITY_FT_MIME)
            return

    def post(self, msg):
        if self._text_channel is not None:
            self._text_channel.post(msg)
            self._show_alert('Msg posted')

    def __buddy_joined_cb(self, sender, buddy):
        self.buddy_joined.emit(buddy)

    def __buddy_left_cb(self, sender, buddy):
        self.buddy_left.emit(buddy)

    def get_client_name(self):
        return CLIENT + '.' + self.project.get_bundle_id()

    @GObject.property
    def leader(self):
        return self._leader


class _TextChannelWrapper(object):

        def __init__(self, text_chan, conn):
            self._activity_cb = None
            self.activity_close_cb = None
            self._text_chan = text_chan
            self._conn = conn
            self._signal_matches = []
            m = self._text_chan[CHANNEL_INTERFACE].connect_to_signal(
                'Closed', self._closed_cb)
            self._signal_matches.append(m)

        def post(self, msg):
            if msg is not None:
                self._send(json.dumps(msg))

        def _send(self, text):
            logging.debug('Sending text')
            if self._text_chan is not None:
                self._text_chan[CHANNEL_INTERFACE].Send(
                    CHANNEL_TEXT_MESSAGE_TYPE_NORMAL, text)

        def close(self):
            logging.debug('Closing text channel')
            try:
                self._text_chan[CHANNEL_INTERFACE].Close()
            except Exception:
                logging.debug('Channel disappeared!')
                self._closed_cb()

        def _closed_cb(self):
            for match in self._signal_matches:
                match.remove()
            self._signal_matches = []
            self._text_chan = None
            if self._activity_close_cb is not None:
                self._activity_close_cb()

        def set_received_callback(self, callback):
            if self._text_chan is not None:
                self._activity_cb = callback
                m = self._text_chan[CHANNEL_TYPE_TEXT].connect_to_signal(
                    'Received', self._received_cb)
                self._signal_matches.append(m)

        def handle_pending_message(self):
            for identity, timestamp, sender, type_, flags, text in \
                self._text_chan[
                    CHANNEL_TYPE_TEXT].ListPendingMessages(False):
                self._received_cb(identity, timestamp, sender, type_, flags, text)

        def _received_cb(self, identity, timestamp, sender, type_, flags, text):
            logging.debug('_TextChannelWrapper._received_cb %r %s' % (type_, text))
            if type_ != 0:
                return

            msg = json.loads(text)

            if self._activity_cb:
                try:
                    self._text_chan[CHANNEL_INTERFACE_GROUP]
                except Exception:
                    nick = self._conn[
                        CONN_INTERFACE_ALIASING].RequestAliases([sender])[0]
                    buddy = {'nick': nick, 'color': '#000000,#808080'}
                    logging.debug('exception: recieved from sender %r buddy %r' %(sender, buddy))

                else:
                    buddy = self._get_buddy(sender)
                    logging.debug('Else: recieved from sender %r buddy %r' %
                        (sender, buddy))

            else:
                logging.debug('Throwing received message on the floor'
                    ' since there is no callback connected. See'
                    ' set_received_callback')

        def set_closed_callback(self, callback):
            logging.debug('set closed callback')
            self._activity_close_cb = callback

        def _get_buddy(self, cs_handle):
            pservice = presenceservice.get_instance()

            tp_name, tp_path = pservice.get_preferred_connection()
            conn = Connection(tp_name, tp_path)
            group = self._text_chan[CHANNEL_INTERFACE_GROUP]
            my_csh = group.GetSelfHandle()

            if my_csh == cs_handle:
                handle = conn.GetSelfHandle()
            elif (group.GetGroupFlags() &
                  CHANNEL_GROUP_FLAG_CHANNEL_SPECIFIC_HANDLES):
                handle = group.GetHandleOwners([cs_handle])[0]
            else:
                handle = cs_handle

                assert handle != 0

            return pservice.get_buddy_telepathy_handle(
                tp_name, tp_path)


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


class OutgoingBlobTransfer(GObject.GObject):

        def __init__(self, buddy, conn, blob, filename, description, mime):
            GObject.GObject.__init__(self)
            self._state = FT_STATE_NONE
            self._transferred_bytes = 0
            self._socket_address = None
            self._socket = None
            self._splicer = None
            self._conn = conn
            self._blob = blob
            self._create_channel(len(self._blob))

            self.channel = None
            self.buddy = buddy
            self.filename = filename
            self.file_size = None
            self.description = description
            self.mime_type = mime
            self.reason_last_change = FT_REASON_NONE

        def _get_input_stream(self):
            return Gio.MemoryInputStream.new_from_data(self._blob, None)

        def set_channel(self, channel):
            self.channel = channel
            self.channel[CHANNEL_TYPE_FILE_TRANSFER].connect_to_signal(
                'FileTransferStateChanged', self.__state_changed_cb)
            self.channel[CHANNEL_TYPE_FILE_TRANSFER].connect_to_signal(
                'TransferredBytesChanged', self.__transferred_bytes_changed_cb)
            self.channel[CHANNEL_TYPE_FILE_TRANSFER].connect_to_signal(
                'InitialOffsetDefined', self.__initial_offset_defined_cb)

            channel_properties = self.channel[dbus.PROPERTIES_IFACE]

            '''props = channel_properties.GetAll(CHANNEL_TYPE_FILE_TRANSFER)
            self._state = props['State']
            self.filename = props['Filename']
            self.file_size = props['Size']
            self.description = props['Description']
            self.mime_type = props['ContentType']'''

        def _create_channel(self, file_size):
            object_path, properties_ = self._conn.CreateChannel(dbus.Dictionary({
                CHANNEL + '.ChannelType': CHANNEL_TYPE_FILE_TRANSFER,
                CHANNEL + '.TargetHandleType': CONNECTION_HANDLE_TYPE_CONTACT,
                CHANNEL + '.TargetHandle': self.buddy.contact_handle,
                CHANNEL_TYPE_FILE_TRANSFER + '.Filename': self.filename,
                CHANNEL_TYPE_FILE_TRANSFER + '.Description': self.description,
                CHANNEL_TYPE_FILE_TRANSFER + '.Size': file_size,
                CHANNEL_TYPE_FILE_TRANSFER + '.ContentType': self.mime_type,
                CHANNEL_TYPE_FILE_TRANSFER + '.InitialOffset': 0}, signature='sv' ))

            self.set_channel(Channel(self._conn.bus_name, object_path))

            channel_file_transfer = self.channel[CHANNEL_TYPE_FILE_TRANSFER]
            self._socket_address = channel_file_transfer.ProvideFile(
                SOCKET_ADDRESS_TYPE_UNIX, SOCKET_ACCESS_CONTROL_LOCALHOST, '',
                byte_arrays=True)

        def __notify_state_cb(self, file_transfer, pspec):
            if self.props.state == FT_STATE_OPEN:
                self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self._socket.connect(self._socket_address)
                output_stream = Gio.UnixOutputStream.new(
                    self._socket.fileno(), True)
                input_stream = self._get_input_stream()
                output_stream.splice_async(
                    input_stream,
                    Gio.OutputStreamSpliceFlags.CLOSE_SOURCE |
                    Gio.OutputStreamSpliceFlags.CLOSE_TARGET,
                    GLib.PRIORITY_LOW, None, None, None)

        def __transferred_bytes_changed_cb(self, transferred_bytes):
            logging.debug('__transferred_bytes_changed_cb %r', transferred_bytes)
            self.props.transferred_bytes = transferred_bytes

        def _set_transferred_bytes(self, transferred_bytes):
            self._transferred_bytes = transferred_bytes

        def _get_transferred_bytes(self):
            return self._transferred_bytes

        transferred_bytes = GObject.Property(type=int,
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

        state = GObject.Property(type=int, getter=_get_state, setter=_set_state)

        def cancel(self):
            self.channel[CHANNEL].Close()
