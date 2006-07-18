import avahi, dbus, dbus.glib, dbus.dbus_bindings, gobject
import Buddy
import Service
import random
import logging
from sugar import env


def _get_local_ip_address(ifname):
	"""Call Linux specific bits to retrieve our own IP address."""
	import socket
	import sys
	import fcntl

	addr = None
	SIOCGIFADDR = 0x8915
	sockfd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	try:
		ifreq = (ifname + '\0'*32)[:32]
		result = fcntl.ioctl(sockfd.fileno(), SIOCGIFADDR, ifreq)
		addr = socket.inet_ntoa(result[20:24])
	except IOError, exc:
		print "Error getting IP address: %s" % exc
	sockfd.close()
	return addr


class ServiceAdv(object):
	"""Wrapper class to track services from Avahi."""
	def __init__(self, interface, protocol, name, stype, domain):
		self._interface = interface
		self._protocol = protocol
		if type(name) != type(u""):
			raise ValueError("service advertisement name must be unicode.")
		self._name = name
		if type(stype) != type(u""):
			raise ValueError("service advertisement type must be unicode.")
		self._stype = stype
		if type(domain) != type(u""):
			raise ValueError("service advertisement domain must be unicode.")
		self._domain = domain
		self._service = None
		self._resolved = False

	def interface(self):
		return self._interface
	def protocol(self):
		return self._protocol
	def name(self):
		return self._name
	def stype(self):
		return self._stype
	def domain(self):
		return self._domain
	def service(self):
		return self._service
	def set_service(self, service):
		if not isinstance(service, Service.Service):
			raise ValueError("must be a valid service.")
		self._service = service
	def resolved(self):
		return self._resolved
	def set_resolved(self, resolved):
		self._resolved = resolved


_PRESENCE_INTERFACE = "org.laptop.Presence"

class PresenceService(dbus.service.Object):
	def __init__(self):
		# interface -> IP address: interfaces we've gotten events on so far
		self._local_addrs = {}

		# Our owner object
		self._owner = None

		self._buddies = {} 		# nick -> Buddy
		self._services = {}		# (name, type) -> Service
		self._activities = {}	# activity id -> Activity

		# Keep track of stuff we're already browsing with ZC
		self._service_type_browsers = {}
		self._service_browsers = {}
		self._resolve_queue = [] # Track resolve requests

		# Resolved service list
		self._service_advs = []

		# Set up the dbus service we provide
		session_bus = dbus.SessionBus()
		bus_name = dbus.service.BusName('org.laptop.Presence', bus=session_bus)		
		dbus.service.Object.__init__(self, bus_name, '/org/laptop/Presence')

		# Connect to Avahi for mDNS stuff
		self._system_bus = dbus.SystemBus()
		self._mdns_service = dbus.Interface(self._bus.get_object(avahi.DBUS_NAME,
				avahi.DBUS_PATH_SERVER), avahi.DBUS_INTERFACE_SERVER)
		# Start browsing the local mDNS domain
		self._start()

	def _start(self):
		# Always browse .local
		self._new_domain_cb(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC, "local")

		# Connect to Avahi and start looking for stuff
		domain_browser = self._mdns_service.DomainBrowserNew(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC,
						"", avahi.DOMAIN_BROWSER_BROWSE, dbus.UInt32(0))
		db = dbus.Interface(self._system_bus.get_object(avahi.DBUS_NAME, domain_browser), avahi.DBUS_INTERFACE_DOMAIN_BROWSER)
		db.connect_to_signal('ItemNew', self._new_domain_cb_glue)

	def _find_service_adv(self, interface=None, protocol=None, name=None, stype=None, domain=None):
		"""Search a list of service advertisements for ones matching certain criteria."""
		adv_list = []
		for adv in self._service_advs:
			if interface and adv.interface() != interface:
				continue
			if protocol and adv.protocol() != protocol:
				continue
			if name and adv.name() != name:
				continue
			if stype and adv.stype() != stype:
				continue
			if domain and adv.domain() != domain:
				continue
			adv_list.append(adv)
		return adv_list

	def _service_appeared_cb(self, interface, protocol, full_name, stype, domain, flags):
		logging.debug("found service '%s' (%d) of type '%s' in domain '%s' on %i.%i." % (full_name, flags, stype, domain, interface, protocol))

		# Add the service to our unresolved services list
		adv_list = self._find_service_adv(interface=interface, protocol=protocol,
				name=full_name, stype=stype, domain=domain)
		adv = None
		if not adv_list:
			adv = ServiceAdv(interface=interface, protocol=protocol, name=full_name,
					stype=stype, domain=domain)
			self._service_advs.append(adv)
		else:
			adv = adv_list[0]

		# Find out the IP address of this interface, if we haven't already
		if interface not in self._local_addrs.keys():
			ifname = self._server.GetNetworkInterfaceNameByIndex(interface)
			if ifname:
				addr = _get_local_ip_address(ifname)
				if addr:
					self._local_addrs[interface] = addr

		# Decompose service name if we can
		(actid, buddy_name) = Service._decompose_service_name(full_name)

		# FIXME: find a better way of letting the StartPage get everything
		self.emit('new-service-adv', actid, stype)

		# If we care about the service right now, resolve it
		resolve = False
		if actid is not None or stype in self._allowed_service_types:
			resolve = True
		if self._is_special_service_type(stype):
			resolve = True
		if resolve and not adv in self._resolve_queue:
			self._resolve_queue.append(adv)
			gobject.idle_add(self._resolve_service, adv)
		else:
			logging.debug("Do not resolve service '%s' of type '%s', we don't care about it." % (full_name, stype))
			
		return False

	def _service_appeared_cb_glue(self, interface, protocol, name, stype, domain, flags):
		gobject.idle_add(self._service_appeared_cb, interface, protocol, name, stype, domain, flags)

	def _service_disappeared_cb(self, interface, protocol, full_name, stype, domain, flags):
		logging.debug("service '%s' of type '%s' in domain '%s' on %i.%i disappeared." % (full_name, stype, domain, interface, protocol))

		# If it's an unresolved service, remove it from our unresolved list
		adv_list = self._find_service_adv(interface=interface, protocol=protocol,
				name=full_name, stype=stype, domain=domain)
		if not adv_list:
			return False

		# Get the service object; if none, we have nothing left to do
		adv = adv_list[0]
		if adv in self._resolve_queue:
			self._resolve_queue.remove(adv)
		service = adv.service()
		if not service:
			return False

		# Decompose service name if we can
		(actid, buddy_name) = Service._decompose_service_name(full_name)

		# Remove the service from the buddy
		try:
			buddy = self._buddies[buddy_name]
		except KeyError:
			pass
		else:
			buddy.remove_service(service)
			self.emit('service-disappeared', buddy, service)
			if not buddy.is_valid():
				self.emit("buddy-disappeared", buddy)
				del self._buddies[buddy_name]
			self._handle_remove_service_for_activity(service, buddy)

		return False

	def _service_disappeared_cb_glue(self, interface, protocol, name, stype, domain, flags):
		gobject.idle_add(self._service_disappeared_cb, interface, protocol, name, stype, domain, flags)

	def _new_service_type_cb(self, interface, protocol, stype, domain, flags):
		# Are we already browsing this domain for this type? 
		if self._service_browsers.has_key((interface, protocol, stype, domain)):
			return

		# Start browsing for all services of this type in this domain
		s_browser = self._mdns_service.ServiceBrowserNew(interface, protocol, stype, domain, dbus.UInt32(0))
		browser_obj = dbus.Interface(self._system_bus.get_object(avahi.DBUS_NAME, s_browser),
						avahi.DBUS_INTERFACE_SERVICE_BROWSER)
		logging.debug("now browsing for services of type '%s' in domain '%s' on %i.%i ..." % (stype, domain, interface, protocol))
		browser_obj.connect_to_signal('ItemNew', self._service_appeared_cb_glue)
		browser_obj.connect_to_signal('ItemRemove', self._service_disappeared_cb_glue)

		self._service_browsers[(interface, protocol, stype, domain)] = browser_obj
		return False

	def _new_service_type_cb_glue(self, interface, protocol, stype, domain, flags):
		gobject.idle_add(self._new_service_type_cb, interface, protocol, stype, domain, flags)

	def _new_domain_cb(self, interface, protocol, domain, flags=0):
		"""Callback from Avahi when a new domain has been found.  Start
		browsing the new domain."""
		# Only use .local for now...
		if domain != "local":
			return

		# Are we already browsing this domain?
		if self._service_type_browsers.has_key((interface, protocol, domain)):
			return

		# Start browsing this domain for the services its members offer
		try:
			st_browser = self._mdns_service.ServiceTypeBrowserNew(interface, protocol, domain, dbus.UInt32(0))
			browser_obj = dbus.Interface(self._system_bus.get_object(avahi.DBUS_NAME, st_browser),
							avahi.DBUS_INTERFACE_SERVICE_TYPE_BROWSER)
		except dbus.DBusException, exc:
			logging.error("got exception %s while attempting to browse domain %s on %i.%i" % (domain, interface, protocol))
			str_exc = str(exc)
			if str_exc.find("The name org.freedesktop.Avahi was not provided by any .service files") >= 0:
				raise Exception("Avahi does not appear to be running.  '%s'" % str_exc)
			else:
				raise exc
		logging.debug("now browsing domain '%s' on %i.%i ..." % (domain, interface, protocol))
		browser_obj.connect_to_signal('ItemNew', self._new_service_type_cb_glue)
		self._service_type_browsers[(interface, protocol, domain)] = browser_obj
		return False

	def _new_domain_cb_glue(self, interface, protocol, domain, flags=0):
		gobject.idle_add(self._new_domain_cb, interface, protocol, domain, flags)
