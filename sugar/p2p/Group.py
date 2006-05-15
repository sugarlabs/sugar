import avahi

from Buddy import Buddy
from Buddy import Owner
from Buddy import PRESENCE_SERVICE_TYPE
from Service import Service
from sugar.p2p.model.Store import Store
import presence

class Group:
	SERVICE_ADDED = "service_added"
	SERVICE_REMOVED = "service_removed"

	BUDDY_JOIN = "buddy_join"
	BUDDY_LEAVE = "buddy_leave"

	def __init__(self):
		self._service_listeners = []
		self._presence_listeners = []
		self._store = Store(self)
	
	def get_store(self):
		return self._store
	
	def join(self):
		pass
	
	def add_service_listener(self, listener):
		self._service_listeners.append(listener)

	def add_presence_listener(self, listener):
		self._presence_listeners.append(listener)
		
	def _notify_service_added(self, service):
		for listener in self._service_listeners:
			listener(Group.SERVICE_ADDED, service)
	
	def _notify_service_removed(self, service_id):
		for listener in self._service_listeners:
			listener(Group.SERVICE_REMOVED, service_id)

	def _notify_buddy_join(self, buddy):
		for listener in self._presence_listeners:
			listener(Group.BUDDY_JOIN, buddy)
	
	def _notify_buddy_leave(self, buddy):
		for listener in self._presence_listeners:
			listener(Group.BUDDY_LEAVE, buddy)

class LocalGroup(Group):
	def __init__(self):
		Group.__init__(self)

		self._services = {}
		self._buddies = {}

		self._pdiscovery = presence.PresenceDiscovery()
		self._pdiscovery.add_service_listener(self._on_service_change)
		self._pdiscovery.start()

	def get_owner(self):
		return self._owner

	def add_service(self, service):
		sid = (service.get_name(), service.get_type())
		self._services[sid] = service
		self._notify_service_added(service)

	def remove_service(self, service_id):
		self._notify_service_removed(service_id)
		del self._services[service_id]

	def join(self):
		self._owner = Owner(self)
		self._owner.register()

	def get_service(self, name, stype):
		if self._services.has_key((name, stype)):
			return self._services[(name, stype)]
		else:
			return None

	def get_buddy(self, name):
		return self._buddies[name]
	
	def _add_buddy(self, buddy):
		bid = buddy.get_nick_name()
		if not self._buddies.has_key(bid):
			self._buddies[bid] = buddy
			self._notify_buddy_join(buddy)

	def _remove_buddy(self, buddy):
		self._notify_buddy_leave(buddy)
		del self._buddies[buddy.get_nick_name()]
	
	def _on_service_change(self, action, interface, protocol, name, stype, domain, flags):
		if action == presence.ACTION_SERVICE_NEW:
			self._pdiscovery.resolve_service(interface, protocol, name, stype, domain,
											 self._on_service_resolved)
		elif action == presence.ACTION_SERVICE_REMOVED:
			if stype == PRESENCE_SERVICE_TYPE:
				self._remove_buddy(name)
			elif stype.startswith("_olpc"):
				self.remove_service((name, stype))
						
	def _on_service_resolved(self, interface, protocol, name, stype, domain,
							 host, aprotocol, address, port, txt, flags):
		multicast = None
		for prop in avahi.txt_array_to_string_array(txt):
			(key, value) = prop.split('=')
			if key == 'multicast':
				multicast = value

		service = Service(name, stype, port, multicast)
		if stype == PRESENCE_SERVICE_TYPE:
			self._add_buddy(Buddy(service, name))
		elif stype.startswith("_olpc"):
			self.add_service(service)
