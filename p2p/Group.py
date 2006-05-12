import avahi

import presence
from Buddy import *
from Service import *

SERVICE_ADDED = "service_added"
SERVICE_REMOVED = "service_removed"

BUDDY_JOIN = "buddy_join"
BUDDY_LEAVE = "buddy_leave"

class Group:
	def __init__(self):
		self._service_listeners = []
		self._presence_listeners = []
	
	def join(self, buddy):
		pass
	
	def add_service_listener(self, listener):
		self._service_listeners.append(listener)

	def add_presence_listener(self, listener):
		self._presence_listeners.append(listener)
		
	def _notify_service_added(self, service):
		for listener in self._service_listeners:
			listener(SERVICE_ADDED, buddy)
	
	def _notify_service_removed(self, service):
		for listener in self._service_listeners:
			listener(SERVICE_REMOVED,buddy)

	def _notify_buddy_join(self, buddy):
		for listener in self._presence_listeners:
			listener(BUDDY_JOIN, buddy)
	
	def _notify_buddy_leave(self, buddy):
		for listener in self._presence_listeners:
			listener(BUDDY_LEAVE, buddy)

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

	def remove_service(self, sid):
		self._notify_service_removed(service)
		del self._services[sid]

	def join(self):
		self._owner = Owner(self)
		self._owner.register()

	def get_service(self, name, stype):
		return self._services[(name, stype)]

	def get_buddy(self, name):
		return self._buddy[name]
	
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
			service = Service(name, host, address, port)
			if stype == PRESENCE_SERVICE_TYPE:
				self._add_buddy(Buddy(service, name))
			elif stype.startswith("_olpc"):
				self.add_service(service)
