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
            self.activity.connect('shared', self.__shared_cb)

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
        self.shared_project.connect('buddy-joined', self.__buddy_joined_cd)
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
            #TODO: method

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






