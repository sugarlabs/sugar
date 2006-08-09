from gettext import gettext as _

from sugar.activity.Activity import Activity
from sugar.chat.BuddyChat import BuddyChat

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
