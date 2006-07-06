import dbus
import random
import logging

import pygtk
pygtk.require('2.0')
import gtk
import gobject

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
		Activity.__init__(self, _CHAT_ACTIVITY_TYPE)
		self._service = service
		self._chat = BuddyChat(self._service)
	
	def on_connected_to_shell(self):
		self.set_tab_text(self._service.get_name())
		self.set_can_close(True)
		self.set_tab_icon(name = "im")
		self.set_show_tab_icon(True)

		plug = self.gtk_plug()		
		plug.add(self._chat)
		self._chat.show()

		plug.show()
	
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
	def open_chat(self, serialized_service):
		self._parent.open_chat(Service.deserialize(serialized_service))

class ChatListener:
	def __init__(self):
		ChatShellDbusService(self)

		self._chats = {}
	
		self._pservice = PresenceService.get_instance()
		self._pservice.start()
		self._pservice.track_service_type(BuddyChat.SERVICE_TYPE)

	def start(self):
		port = random.randint(5000, 65535)
		service = Service.Service(sugar.env.get_nick_name(), BuddyChat.SERVICE_TYPE,
						  		  'local', '', port)
		self._buddy_stream = Stream.new_from_service(service)
		self._buddy_stream.set_data_listener(self._recv_message)
		self._pservice.register_service(service)

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
		
	def open_chat(self, service):
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
