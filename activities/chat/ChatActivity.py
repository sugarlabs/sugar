import dbus
import random
import logging

import gtk
import gobject
from gettext import gettext as _

from sugar.activity.Activity import Activity
from sugar.presence import Service
from sugar.chat.Chat import Chat
from sugar.chat.BuddyChat import BuddyChat
from sugar.p2p.Stream import Stream
from sugar.presence.PresenceService import PresenceService
import sugar.env

_CHAT_ACTIVITY_TYPE = "_chat_activity_type._tcp"

class ChatActivity(Activity):
	def __init__(self, service):
		Activity.__init__(self)
		self.set_title(_('Private chat'))

		self._service = service
		self._chat = BuddyChat(self._service)
		self.add(self._chat)
		self._chat.show()		

	def recv_message(self, message):
		self._chat.recv_message(message)

class ChatShellDbusService(dbus.service.Object):
	def __init__(self, parent):
		self._parent = parent
		session_bus = dbus.SessionBus()
		bus_name = dbus.service.BusName('com.redhat.Sugar.Chat', bus=session_bus)
		object_path = '/com/redhat/Sugar/Chat'
		dbus.service.Object.__init__(self, bus_name, object_path)

	@dbus.service.method('com.redhat.Sugar.ChatShell')
	def open_chat(self, service_path):
		self._parent.open_chat(service_path)

class ChatListener:
	def __init__(self):
		ChatShellDbusService(self)

		self._chats = {}
	
		self._pservice = PresenceService()
		self._pservice.register_service_type(BuddyChat.SERVICE_TYPE)

	def start(self):
		self._service = self._pservice.register_service(sugar.env.get_nick_name(),
				BuddyChat.SERVICE_TYPE)
		self._buddy_stream = Stream.new_from_service(self._service)
		self._buddy_stream.set_data_listener(self._recv_message)

	def _recv_message(self, address, message):
		[nick, msg] = Chat.deserialize_message(message)
		buddy = self._pservice.get_buddy_by_nick_name(nick)
		if buddy:
			if buddy == self._pservice.get_owner():
				return		
			service = buddy.get_service_of_type(BuddyChat.SERVICE_TYPE)
			name = service.get_name()
			if service:
				if not self._chats.has_key(name):
					self.open_chat(service)
				self._chats[name].recv_message(message)			
			else:
				logging.error('The buddy %s does not have a chat service.' % (nick))
		else:
			logging.error('The buddy %s is not present.' % (nick))
			return
		
	def open_chat(self, service_path):
		service = self._pservice._new_object(service_path)
		chat = ChatActivity(service)
		self._chats[service.get_name()] = chat
		gobject.idle_add(self._connect_chat, chat)
		return chat

	def _connect_chat(self, chat):
		chat.connect_to_shell()
		return False

def start():
	chat_listener = ChatListener()
	chat_listener.start()
