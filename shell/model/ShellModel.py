import gobject

from sugar.presence import PresenceService
from model.Friends import Friends
from model.Invites import Invites
from model.Owner import ShellOwner

class ShellModel(gobject.GObject):
	__gsignals__ = {
		'activity-opened':  (gobject.SIGNAL_RUN_FIRST,
							 gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT])),
		'activity-changed': (gobject.SIGNAL_RUN_FIRST,
							 gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT])),
		'activity-closed':  (gobject.SIGNAL_RUN_FIRST,
							 gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT]))
	}

	def __init__(self):
		gobject.GObject.__init__(self)

		self._hosts = {}
		self._current_activity = None

		PresenceService.start()
		self._pservice = PresenceService.get_instance()

		self._owner = ShellOwner()
		self._owner.announce()
		self._friends = Friends()
		self._invites = Invites()

	def get_friends(self):
		return self._friends

	def get_invites(self):
		return self._invites

	def get_owner(self):
		return self._owner

	def add_activity(self, activity_host):
		self._hosts[activity_host.get_xid()] = activity_host
		self.emit('activity-opened', activity_host)

	def set_current_activity(self, activity_xid):
		activity_host = self._hosts[activity_xid]
		if self._current_activity == activity_host:
			return

		self._current_activity = activity_host
		self.emit('activity-changed', activity_host)

	def remove_activity(self, activity_xid):
		if self._hosts.has_key(activity_xid):
			host = self._hosts[activity_xid]
			self.emit('activity-closed', host)
			del self._hosts[activity_xid]

	def get_activity(self, activity_id):
		for host in self._hosts.values():
			if host.get_id() == activity_id:
				return host
		return None

	def get_current_activity(self):
		return self._current_activity
