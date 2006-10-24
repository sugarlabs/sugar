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
from sugar.chat.Chat import Chat
from sugar.p2p.Stream import Stream

class ChatActivity(Activity):
	def __init__(self):
		Activity.__init__(self)

		self._group_stream = None

		self.set_title(_('Group chat'))

		self._chat = Chat()
		self.add(self._chat)
		self._chat.show()

	def join(self, activity_ps):
		Activity.join(self, activity_ps)
		self._setup_stream()

	def share(self):
		Activity.share(self)
		self._setup_stream()

	def _setup_stream(self):
		self._group_stream = Stream.new_from_service(self._service)
		self._group_stream.set_data_listener(self._group_recv_message)
		self._chat.set_stream_writer(self._group_stream.new_writer())

	def _group_recv_message(self, address, msg):
		self._chat.recv_message(msg)
