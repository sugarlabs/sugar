import presence
import avahi

ACTION_BUDDY_ADDED = "added"
ACTION_BUDDY_REMOVED = "removed"


class Buddy(object):
	def __init__(self, nick, realname, servicename, key=None):
		self._nick = nick
		self._realname = realname
		self._servicename = servicename
		self._key = key

	def nick(self):
		return self._nick

	def realname(self):
		return self._realname

	def servicename(self):
		return self._servicename

	def key(self):
		return self._key

class BuddyList(object):
	""" Manage a list of buddies """

	def __init__(self):
		self._listeners = []
		self._buddies = {}
		self._pdiscovery = presence.PresenceDiscovery()
		self._pdiscovery.add_service_listener(self._on_service_change)
		self._pdiscovery.start()

	def add_buddy_listener(self, listener):
		self._listeners.append(listener)

	def _add_buddy(self, host, address, servicename, data):
		if len(data) > 0 and 'name' in data.keys():
			buddy = Buddy(data['name'], data['realname'], servicename)
			self._buddies[data['name']] = buddy
			self._notify_listeners(ACTION_BUDDY_ADDED, buddy)

	def _remove_buddy(self, buddy):
		nick = buddy.nick()
		self._notify_listeners(ACTION_BUDDY_REMOVED, buddy)
		del self._buddies[nick]

	def _find_buddy_by_service_name(self, servicename):
		for buddy in self._buddies.keys():
			if buddy.servicename() == servicename:
				return buddy
		return None

	def _notify_listeners(self, action, buddy):
		for listener in self._listeners:
			listener(action, buddy)

	def _on_service_change(self, action, interface, protocol, name, stype, domain, flags):
		if stype != presence.OLPC_CHAT_SERVICE:
			return
		if action == presence.ACTION_SERVICE_NEW:
			self._pdiscovery.resolve_service(interface, protocol, name, stype, domain, self._on_service_resolved)
		elif action == presence.ACTION_SERVICE_REMOVED:
			buddy = self._find_buddy_by_service_name(name)
			if buddy:
				self._remove_buddy(buddy)

	def _pair_to_dict(self, l):
		res = {}
		for el in l:
			tmp = el.split('=', 1)
			if len(tmp) > 1:
				res[tmp[0]] = tmp[1]
			else:
				res[tmp[0]] = ''
		return res

	def _on_service_resolved(self, interface, protocol, name, stype, domain, host, aprotocol, address, port, txt, flags):
		data = self._pair_to_dict(avahi.txt_array_to_string_array(txt))
		self._add_buddy(host, address, name, data)

