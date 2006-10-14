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

from sugar.presence import PresenceService
from model.Friends import Friends
from model.MeshModel import MeshModel
from model.Owner import ShellOwner

class ShellModel:
	def __init__(self):
		self._current_activity = None

		PresenceService.start()
		self._pservice = PresenceService.get_instance()

		self._owner = ShellOwner()
		self._owner.announce()
		self._friends = Friends()
		self._mesh = MeshModel()

	def get_mesh(self):
		return self._mesh

	def get_friends(self):
		return self._friends

	def get_invites(self):
		return self._owner.get_invites()

	def get_owner(self):
		return self._owner

	def set_current_activity(self, activity_id):
		self._current_activity = activity_id
		self._owner.set_current_activity(activity_id)

	def get_current_activity(self):
		return self._current_activity
