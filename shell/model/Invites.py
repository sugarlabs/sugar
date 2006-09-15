import gobject

import conf
from sugar.presence import PresenceService
from sugar.canvas.IconColor import IconColor

class Invite:
	def __init__(self, issuer, bundle_id, activity_id):
		self._issuer = issuer
		self._activity_id = activity_id
		self._bundle_id = bundle_id

	def get_icon(self):
		reg = conf.get_activity_registry()
		return reg.get_activity(self._bundle_id).get_icon()

	def get_color(self):
		pservice = PresenceService.get_instance()
		buddy = pservice.get_buddy_by_name(self._issuer)
		if buddy != None:
			return IconColor(buddy.get_color())
		else:
			return IconColor('white')

	def get_activity_id(self):
		return self._activity_id

	def get_bundle_id(self):
		return self._bundle_id

class Invites(gobject.GObject):
	__gsignals__ = {
		'invite-added':   (gobject.SIGNAL_RUN_FIRST,
						   gobject.TYPE_NONE, ([object])),
		'invite-removed': (gobject.SIGNAL_RUN_FIRST,
						   gobject.TYPE_NONE, ([object])),
	}

	def __init__(self):
		gobject.GObject.__init__(self)

		self._list = []

	def add_invite(self, issuer, bundle_id, activity_id):
		invite = Invite(issuer, bundle_id, activity_id)
		self._list.append(invite)
		self.emit('invite-added', invite)

	def remove_invite(self, invite):
		self._list.remove(invite)
		self.emit('invite-removed', invite)

	def __iter__(self):
		return self._list.__iter__()
