from gettext import gettext as _

from sugar.activity.Activity import Activity
from sugar.chat.BuddyChat import BuddyChat
from sugar.presence.PresenceService import PresenceService

class ChatActivity(Activity):
	def __init__(self):
		Activity.__init__(self)
		self.set_title(_('Private chat'))

	def cmd_connect(self, args):
		pservice = PresenceService()
		service = pservice.get(args[0])

		self._chat = BuddyChat(service)
		self.add(self._chat)
		self._chat.show()		

	def cmd_message(self, args):
		self._chat.recv_message(args[0])

	def execute(self, command, args):
		if command == 'connect':
			self.cmd_connect(args)
		elif command == 'message':
			self.cmd_message(args)
		
