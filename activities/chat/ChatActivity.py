import dbus
import random

import pygtk
pygtk.require('2.0')
import gtk

from sugar.activity.Activity import Activity
from sugar.LogWriter import LogWriter
from sugar.presence.Service import Service
from sugar.chat.BuddyChat import BuddyChat
from sugar.p2p.Stream import Stream
from sugar.presence.PresenceService import PresenceService
import sugar.env

_CHAT_ACTIVITY_TYPE = "_chat_activity_type._tcp"

class ChatActivity(Activity):
	def __init__(self, service):
		Activity.__init__(self, _GMAIL_ACTIVITY_TYPE)
		self._service = service
	
	def on_connected_to_shell(self):
		self.set_can_close(True)
		self.set_tab_icon(icon_name="im")
		self.set_show_tab_icon(True)

		plug = self.gtk_plug()		

		chat = BuddyChat(self._service)
		plug.add(chat)
		chat.show()

		plug.show()

class ChatShellDbusService(dbus.service.Object):
	def __init__(self, parent):
		self._parent = parent
		session_bus = dbus.SessionBus()
		bus_name = dbus.service.BusName('com.redhat.Sugar.Chat', bus=session_bus)
		object_path = '/com/redhat/Sugar/Chat'
		dbus.service.Object.__init__(self, bus_name, object_path)

	@dbus.service.method('com.redhat.Sugar.ChatShell')
	def open_chat(self, message):
		self._parent.send_text_message(message)

class ChatShell:
	instance = None

	def get_instance():
		if not ChatShell.instance:
			ChatShell.instance = ChatShell()
		return ChatShell.instance		
	get_instance = staticmethod(get_instance)

	def __init__(self):
		self._pservice = PresenceService.get_instance()
		self._pservice.start()
		self._pservice.track_service_type(BuddyChat.SERVICE_TYPE)

	def start(self):
		port = random.randint(5000, 65535)
		service = Service(sugar.env.get_nick_name(), BuddyChat.SERVICE_TYPE,
						  'local', '', port)
		self._buddy_stream = Stream.new_from_service(service)
		self._buddy_stream.set_data_listener(getattr(self, "_recv_message"))
		self._pservice.register_service(service)

	def _recv_message(self, address, msg):
		print msg
		
	def open_chat(self, serialized_service):
		service = Service.deserialize(serialized_service)
		self._chat = ChatActivity(service)
		self._chat.connect_to_shell()

log_writer = LogWriter("Chat")
log_writer.start()

chat_shell = ChatShell.get_instance()
chat_shell.start()

gtk.main()
