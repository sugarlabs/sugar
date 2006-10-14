# Copyright (C) 2006, Red Hat, Inc.
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
		
