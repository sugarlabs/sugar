# Copyright (C) 2006, Red Hat, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

from sugar.chat.Chat import Chat
from sugar.p2p.Stream import Stream

class BuddyChat(Chat):
	SERVICE_TYPE = "_olpc_buddy_chat._tcp"

	def __init__(self, service):
		Chat.__init__(self)

		self._stream = Stream.new_from_service(service, False)
		self._stream_writer = self._stream.new_writer(service)

	def _recv_message_cb(self, address, msg):
		self.recv_message(msg)
