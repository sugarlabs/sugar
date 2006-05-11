# -*- tab-width: 4; indent-tabs-mode: t -*- 

import avahi, dbus, dbus.glib

OLPC_CHAT_SERVICE = "_olpc_chat._udp"

ACTION_SERVICE_NEW = 'new'
ACTION_SERVICE_REMOVED = 'removed'

class PresenceDiscovery(object):
	def __init__(self):
		self.bus = dbus.SystemBus()
		self.server = dbus.Interface(self.bus.get_object(avahi.DBUS_NAME, avahi.DBUS_PATH_SERVER), avahi.DBUS_INTERFACE_SERVER)
		self._service_browsers = {}
		self._service_type_browsers = {}
		self._service_listeners = []

	def add_service_listener(self, listener):
		self._service_listeners.append(listener)

	def start(self):
		# Always browse .local
		self.browse_domain(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC, "local")
		db = dbus.Interface(self.bus.get_object(avahi.DBUS_NAME, self.server.DomainBrowserNew(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC, "", avahi.DOMAIN_BROWSER_BROWSE, dbus.UInt32(0))), avahi.DBUS_INTERFACE_DOMAIN_BROWSER)
		db.connect_to_signal('ItemNew', self.new_domain)	

	def _error_handler(self, err):
		print "Error resolving: %s" % err

	def resolve_service(self, interface, protocol, name, stype, domain, reply_handler, error_handler=None):
		if not error_handler:
			error_handler = self._error_handler
		self.server.ResolveService(int(interface), int(protocol), name, stype, domain, avahi.PROTO_UNSPEC, dbus.UInt32(0), reply_handler=reply_handler, error_handler=error_handler)

	def new_service(self, interface, protocol, name, stype, domain, flags):
		print "Found service '%s' (%d) of type '%s' in domain '%s' on %i.%i." % (name, flags, stype, domain, interface, protocol)
		for listener in self._service_listeners:
			listener(ACTION_SERVICE_NEW, interface, protocol, name, stype, domain, flags)

	def remove_service(self, interface, protocol, name, stype, domain, flags):
#		print "Service '%s' of type '%s' in domain '%s' on %i.%i disappeared." % (name, stype, domain, interface, protocol)
		for listener in self._service_listeners:
			listener(ACTION_SERVICE_REMOVED, interface, protocol, name, stype, domain, flags)
 
	def new_service_type(self, interface, protocol, stype, domain, flags):
		# Are we already browsing this domain for this type? 
		if self._service_browsers.has_key((interface, protocol, stype, domain)):
			return

#		print "Browsing for services of type '%s' in domain '%s' on %i.%i ..." % (stype, domain, interface, protocol)

		b = dbus.Interface(self.bus.get_object(avahi.DBUS_NAME, self.server.ServiceBrowserNew(interface, protocol, stype, domain, dbus.UInt32(0))),  avahi.DBUS_INTERFACE_SERVICE_BROWSER)
		b.connect_to_signal('ItemNew', self.new_service)
		b.connect_to_signal('ItemRemove', self.remove_service)

		self._service_browsers[(interface, protocol, stype, domain)] = b

	def browse_domain(self, interface, protocol, domain):
		# Are we already browsing this domain?
		if self._service_type_browsers.has_key((interface, protocol, domain)):
			return

#		print "Browsing domain '%s' on %i.%i ..." % (domain, interface, protocol)
    
		b = dbus.Interface(self.bus.get_object(avahi.DBUS_NAME, self.server.ServiceTypeBrowserNew(interface, protocol, domain, dbus.UInt32(0))),  avahi.DBUS_INTERFACE_SERVICE_TYPE_BROWSER)
		b.connect_to_signal('ItemNew', self.new_service_type)

		self._service_type_browsers[(interface, protocol, domain)] = b

	def new_domain(self,interface, protocol, domain, flags):
		if domain != "local":
			return
		self.browse_domain(interface, protocol, domain)


class PresenceAnnounce(object):
	def __init__(self):
		self.bus = dbus.SystemBus()
		self.server = dbus.Interface(self.bus.get_object(avahi.DBUS_NAME, avahi.DBUS_PATH_SERVER), avahi.DBUS_INTERFACE_SERVER)
		self._hostname = None

	def register_service(self, rs_name, rs_port, rs_service, **kwargs):
		g = dbus.Interface(self.bus.get_object(avahi.DBUS_NAME, self.server.EntryGroupNew()), avahi.DBUS_INTERFACE_ENTRY_GROUP)

		if rs_name is None:
			if self._hostname is None:
				self._hostname = "%s:%s" % (self.server.GetHostName(), rs_port)
				rs_name = self._hostname

		info = ["%s=%s" % (k,v) for k,v in kwargs.items()]
		g.AddService(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC, 0, rs_name, rs_service,
				"", "", # domain, host (let the system figure it out)
				dbus.UInt16(rs_port), info,)
		g.Commit()
		return g
