import avahi

import presence
from Buddy import *
from Service import *

BUDDY_JOIN = "join"
BUDDY_LEAVE = "leave"

class Group:
	def __init__(self):
		self._listeners = []
	
	def join(self, buddy):
		pass
	
	def add_listener(self, group_listener):
		self._listeners.append(group_listener)
		
	def _notify_buddy_join(self, buddy):
		for listener in self._listeners:
			listener(BUDDY_JOIN, buddy)
	
	def _notify_buddy_leave(self, buddy):
		for listener in self._listeners:
			listener(BUDDY_LEAVE,buddy)

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

	def join(self):
		self._owner = Owner()
		self._owner.register()

	def get_service_from_name(self, name):
		if name == 'localgroup_multicast':
			return Service('localgroup_multicast', '', '224.0.0.221', 6666, True)
		elif name == self._owner.get_service().get_name():
			return self._owner.get_service()
		else:
			return self._services[name]
	
	def get_buddy_from_address(self, address):
		for buddy in self._buddies.values():
			if buddy.get_service().get_address() == address:
				return buddy
		return None

	def _on_service_change(self, action, interface, protocol, name, stype, domain, flags):
		if action == presence.ACTION_SERVICE_NEW:
			self._pdiscovery.resolve_service(interface, protocol, name, stype, domain,
											 self._on_service_resolved)
		elif action == presence.ACTION_SERVICE_REMOVED:
			del self._services[name]
			self._remove_buddy(name)
						
	def _on_service_resolved(self, interface, protocol, name, stype, domain,
							 host, aprotocol, address, port, txt, flags):
		service = Service(name, host, address, port)
		self._services[name] = service
		if stype == BUDDY_SERVICE_TYPE:
			data = self._pair_to_dict(avahi.txt_array_to_string_array(txt))
			self._add_buddy(service, data)

	def _add_buddy(self, service, data):
		name = service.get_name()
		if not self._buddies.has_key(name):
			buddy = Buddy(service, data['nickname'])
			self._buddies[name] = buddy
			self._notify_buddy_join(buddy)
	
	def _remove_buddy(self, name):
		self._notify_buddy_leave(self._buddies[name])
		del self._buddies[name]
		
	def _pair_to_dict(self, l):
		res = {}
		for el in l:
			tmp = el.split('=', 1)
			if len(tmp) > 1:
				res[tmp[0]] = tmp[1]
			else:
				res[tmp[0]] = ''
		return res
