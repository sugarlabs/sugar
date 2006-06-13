import threading
import avahi, dbus, dbus.glib, dbus.dbus_bindings, gobject
import Buddy
import Service
import Group
import os


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


class PresenceService(gobject.GObject):
	"""Object providing information about the presence of Buddies
	and what activities they make available to others."""

	__gsignals__ = {
		'buddy-appeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([gobject.TYPE_PYOBJECT])),
		'buddy-disappeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([gobject.TYPE_PYOBJECT]))
	}

	__lock = threading.Lock()
	__instance = None

	def get_instance():
		"""Return, creating if needed, the singleton PresenceService
		object."""
		PresenceService.__lock.acquire()
		if not PresenceService.__instance:
			PresenceService.__instance = PresenceService()
		PresenceService.__lock.release()
		return PresenceService.__instance
	get_instance = staticmethod(get_instance)

	def __init__(self, debug=False):
		gobject.GObject.__init__(self)

		self._debug = debug
		self._lock = threading.Lock()
		self._started = False

		# interface -> IP address: interfaces we've gotten events on so far
		self._local_addrs = {}

		# nick -> Buddy: buddies we've found
		self._buddies = {}
		# Our owner object
		self._owner = None

		# group UID -> Group: groups we've found
		self._groups = {}

		# All the mdns service types we care about
		self._allowed_service_types = []

		# Keep track of stuff we're already browsing with ZC
		self._service_type_browsers = {}
		self._service_browsers = {}

		# We only resolve services that our clients are interested in;
		# but we store unresolved services so that when a client does
		# become interested in a new service type, we can quickly
		# resolve it
		self._unresolved_services = []

		self._bus = dbus.SystemBus()
		self._server = dbus.Interface(self._bus.get_object(avahi.DBUS_NAME,
				avahi.DBUS_PATH_SERVER), avahi.DBUS_INTERFACE_SERVER)

	def start(self):
		"""Start the presence service by kicking off service discovery."""
		self._lock.acquire()
		if self._started:
			self._lock.release()
			return
		self._started = True
		self._lock.release()

		# Always browse .local
		self._new_domain_cb(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC, "local")

		# Connect to Avahi and start looking for stuff
		domain_browser = self._server.DomainBrowserNew(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC, "", avahi.DOMAIN_BROWSER_BROWSE, dbus.UInt32(0))
		db = dbus.Interface(self._bus.get_object(avahi.DBUS_NAME, domain_browser), avahi.DBUS_INTERFACE_DOMAIN_BROWSER)
		db.connect_to_signal('ItemNew', self._new_domain_cb_glue)

	def set_debug(self, debug):
		self._debug = debug

	def _log(self, msg):
		"""Simple logger."""
		if self._debug:
			print "PresenceService(%d): %s" % (os.getpid(), msg)

	def get_owner(self):
		"""Return the owner of this machine/instance, if we've recognized them yet."""
		return self._owner

	def _resolve_service_error_handler(self, err):
		self._log("error resolving service: %s" % err)

	def _find_service(self, slist, name=None, stype=None, domain=None, address=None, port=None):
		"""Search a list of services for ones matching certain criteria."""
		found = []
		for service in slist:
			if name and service.get_name() != name:
				continue
			if stype and service.get_type() != stype:
				continue
			if domain and service.get_domain() != domain:
				continue
			if address and service.get_address() != address:
				continue
			if port and service.get_port() != port:
				continue
			found.append(service)
		return found

	def _is_special_service_type(self, stype):
		"""Return True if the service type is a special, internal service
		type, and False if it's not."""
		if stype == Buddy.PRESENCE_SERVICE_TYPE:
			return True
		if Group.is_group_service_type(stype):
			return True
		return False

	def _handle_new_service_for_buddy(self, service):
		"""Deal with a new discovered service object."""
		# Once a service is resolved, we match it up to an existing buddy,
		# or create a new Buddy if this is the first service known about the buddy
		added = was_valid = False
		name = service.get_name()
		buddy = None
		try:
			buddy = self._buddies[name]
			was_valid = buddy.is_valid()
			added = buddy.add_service(service)
		except KeyError:
			# Should this service mark the owner?
			if service.get_address() in self._local_addrs.values():
				buddy = Buddy.Owner(service)
				self._owner = buddy
			else:
				buddy = Buddy.Buddy(service)
			self._buddies[name] = buddy
			added = True
		if not was_valid and buddy.is_valid():
			self.emit("buddy-appeared", buddy)
		return buddy

	def _handle_new_service_for_group(self, service, buddy):
		# If the serivce is a group service, merge it into our groups list
		if not buddy:
			return
		group = None
		if not self._groups.has_key(service.get_type()):
			group = Group.Group(service)
		else:
			group = self._groups[service.get_type()]

	def _resolve_service_reply_cb(self, interface, protocol, name, stype, domain, host, aprotocol, address, port, txt, flags):
		"""When the service discovery finally gets here, we've got enough information about the
		service to assign it to a buddy."""
		self._log("resolved service '%s' type '%s' domain '%s' to %s:%s" % (name, stype, domain, address, port))

		# If this service was previously unresolved, remove it from the
		# unresolved list
		found = self._find_service(self._unresolved_services, name=name,
				stype=stype, domain=domain)
		if not len(found):
			return False
		for service in found:
			self._unresolved_services.remove(service)

		# Update the service now that it's been resolved
		service = found[0]
		service.set_address(address)
		service.set_port(port)
		service.set_properties(txt)

		# Merge the service into our buddy and group lists, if needed
		buddy = self._handle_new_service_for_buddy(service)
		if service.is_group_service():
			self._handle_new_service_for_group(service, buddy)

		return False

	def _resolve_service_reply_cb_glue(self, interface, protocol, name, stype, domain, host, aprotocol, address, port, txt, flags):
		gobject.idle_add(self._resolve_service_reply_cb, interface, protocol,
				name, stype, domain, host, aprotocol, address, port, txt, flags)

	def _resolve_service(self, interface, protocol, name, stype, domain, flags):
		"""Resolve and lookup a ZeroConf service to obtain its address and TXT records."""
		# Ask avahi to resolve this particular service
		self._server.ResolveService(int(interface), int(protocol), name,
				stype, domain, avahi.PROTO_UNSPEC, dbus.UInt32(0), # use flags here maybe?
				reply_handler=self._resolve_service_reply_cb_glue,
				error_handler=self._resolve_service_error_handler)
		return False

	def _service_appeared_cb(self, interface, protocol, name, stype, domain, flags):
		self._log("found service '%s' (%d) of type '%s' in domain '%s' on %i.%i." % (name, flags, stype, domain, interface, protocol))

		# Add the service to our unresolved services list
		found = self._find_service(self._unresolved_services, name=name,
				stype=stype, domain=domain)
		if not len(found):
			service = Service.Service(name, stype, domain)
			self._unresolved_services.append(service)

		# Find out the IP address of this interface, if we haven't already
		if interface not in self._local_addrs.keys():
			ifname = self._server.GetNetworkInterfaceNameByIndex(interface)
			if ifname:
				addr = _get_local_ip_address(ifname)
				if addr:
					self._local_addrs[interface] = addr

		# If we care about the service right now, resolve it
		if stype in self._allowed_service_types or self._is_special_service_type(stype):
			gobject.idle_add(self._resolve_service, interface, protocol, name, stype, domain, flags)
		return False

	def _service_appeared_cb_glue(self, interface, protocol, name, stype, domain, flags):
		gobject.idle_add(self._service_appeared_cb, interface, protocol, name, stype, domain, flags)

	def _service_disappeared_cb(self, interface, protocol, name, stype, domain, flags):
		self._log("service '%s' of type '%s' in domain '%s' on %i.%i disappeared." % (name, stype, domain, interface, protocol))
		# If it's an unresolved service, remove it from our unresolved list
		found = self._find_service(self._unresolved_services, name=name,
				stype=stype, domain=domain)
		for service in found:
			self._unresolved_services.remove(service)

		# Unresolved services by definition aren't assigned to a buddy
		if not len(found):
			try:
				# Remove the service from the buddy
				buddy = self._buddies[name]
				# FIXME: need to be more careful about how we remove services
				# from buddies; this could be spoofed
				service = buddy.get_service_of_type(stype)
				buddy.remove_service(service)
				if not buddy.is_valid():
					self.emit("buddy-disappeared", buddy)
					del self._buddies[name]
			except KeyError:
				pass

		return False

	def _service_disappeared_cb_glue(self, interface, protocol, name, stype, domain, flags):
		gobject.idle_add(self._service_disappeared_cb, interface, protocol, name, stype, domain, flags)

	def _new_service_type_cb(self, interface, protocol, stype, domain, flags):
		# Are we already browsing this domain for this type? 
		if self._service_browsers.has_key((interface, protocol, stype, domain)):
			return

		# Start browsing for all services of this type in this domain
		s_browser = self._server.ServiceBrowserNew(interface, protocol, stype, domain, dbus.UInt32(0))
		browser_obj = dbus.Interface(self._bus.get_object(avahi.DBUS_NAME, s_browser), avahi.DBUS_INTERFACE_SERVICE_BROWSER)
		self._log("now browsing for services of type '%s' in domain '%s' on %i.%i ..." % (stype, domain, interface, protocol))
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
			st_browser = self._server.ServiceTypeBrowserNew(interface, protocol, domain, dbus.UInt32(0))
			browser_obj = dbus.Interface(self._bus.get_object(avahi.DBUS_NAME, st_browser), avahi.DBUS_INTERFACE_SERVICE_TYPE_BROWSER)
		except dbus.DBusException, exc:
			self._log("got exception %s while attempting to browse domain %s on %i.%i" % (domain, interface, protocol))
			str_exc = str(exc)
			if str_exc.find("The name org.freedesktop.Avahi was not provided by any .service files") >= 0:
				raise Exception("Avahi does not appear to be running.  '%s'" % str_exc)
			else:
				raise exc
		self._log("now browsing domain '%s' on %i.%i ..." % (domain, interface, protocol))
		browser_obj.connect_to_signal('ItemNew', self._new_service_type_cb_glue)
		self._service_type_browsers[(interface, protocol, domain)] = browser_obj
		return False

	def _new_domain_cb_glue(self, interface, protocol, domain, flags=0):
		gobject.idle_add(self._new_domain_cb, interface, protocol, domain, flags)

	def track_service_type(self, stype):
		"""Requests that the Presence service look for and recognize
		a certain mDNS service types."""
		if not self._started:
			raise RuntimeError("presence service must be started first.")
		if not type(stype) == type(""):
			raise ValueError("service type must be a string.")
		if self._is_special_service_type(stype):
			return
		if stype in self._allowed_service_types:
			return

		self._allowed_service_types.append(stype)

		# Find unresolved services that match the service type
		# we're now interested in, and resolve them
		found = self._find_service(self._unresolved_services, stype=stype)
		for service in found:
			gobject.idle_add(self._resolve_service, interface, protocol, name, stype, domain, flags)

	def untrack_service_type(self, stype):
		"""Stop tracking a certain mDNS service."""
		if not self._started:
			raise RuntimeError("presence service must be started first.")
		if not type(stype) == type(""):
			raise ValueError("service type must be a string.")
		if name in self._allowed_service_types:
			self._allowed_service_types.remove(stype)

	def register_service(self, service):
		"""Register a new service, advertising it to other Buddies on the network."""
		if not self._started:
			raise RuntimeError("presence service must be started first.")

		rs_name = service.get_name()
		rs_stype = service.get_type()
		rs_port = service.get_port()
		if type(rs_port) != type(1) and rs_port <= 1024:
			raise ValueError("invalid service port.")
		rs_props = service.get_properties()
		rs_domain = service.get_domain()
		if not rs_domain or not len(rs_domain):
			rs_domain = ""
		self._log("registered service name '%s' type '%s' on port %d with args %s" % (rs_name, rs_stype, rs_port, rs_props))

		try:
			group = dbus.Interface(self._bus.get_object(avahi.DBUS_NAME, self._server.EntryGroupNew()), avahi.DBUS_INTERFACE_ENTRY_GROUP)
			info = ["%s=%s" % (k, v) for k, v in rs_props.items()]
			group.AddService(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC, 0, rs_name, rs_stype,
					rs_domain, "", # let Avahi figure the 'host' out
					dbus.UInt16(rs_port), info,)
			group.Commit()
		except dbus.dbus_bindings.DBusException, exc:
			# FIXME: ignore local name collisions, since that means
			# the zeroconf service is already registered.  Ideally we
			# should un-register it an re-register with the correct info
			if str(exc) == "Local name collision":
				pass
		self.track_service_type(rs_stype)
		return group

	def get_buddy_by_nick_name(self, nick_name):
		"""Look up and return a buddy by nickname."""
		if self._buddies.has_key(nick_name):
			return self._buddies[nick_name]
		return None

	def get_buddy_by_address(self, address):
		for buddy in self._buddies.values():
			if buddy.get_address == address:
				return buddy
		return None

	def get_buddies(self):
		"""Return the entire buddy list."""
		return self._buddies.values()

#################################################################
# Tests
#################################################################

import unittest

ps = None

class PresenceServiceTestCase(unittest.TestCase):
	_DEF_NAME = "Paul"
	_DEF_STYPE = Buddy.PRESENCE_SERVICE_TYPE
	_DEF_DOMAIN = "local"
	_DEF_PORT = 3333
	_DEF_PROPERTIES = {"foo": "bar", "bork": "baz"}

	def testNoServices(self):
		"""Ensure that no services are found initially."""
		"""This test may illegitimately fail if there's another person
		on the network running sugar...  So its usefulness is somewhat
		dubious."""
		import gtk
		global ps
		buddies = ps.get_buddies()
		assert len(buddies) == 0, "A buddy was found without setting tracked services!"
		gtk.main_quit()

	def testServiceRegistration(self):
		service = Service.Service(self._DEF_NAME, self._DEF_STYPE, self._DEF_DOMAIN,
				address=None, port=self._DEF_PORT, properties=self._DEF_PROPERTIES)
		global ps
		ps.register_service(service)
		# Give the Presence Service some time to find the new service
		gobject.timeout_add(2000, self.quitMain)
		import gtk
		gtk.main()

	def quitMain(self):
		import gtk
		gtk.main_quit()

	def testServiceDetection(self):
		global ps
		buddy = ps.get_buddy_by_nick_name("Paul")
		assert buddy, "The registered buddy was not found after 2 seconds!"
		assert buddy.is_valid(), "The buddy was invalid, since no presence was advertised."
		assert buddy.is_owner() == True, "The buddy was not the owner, but it should be!"

	def addToSuite(suite):
		suite.addTest(PresenceServiceTestCase("testNoServices"))
		suite.addTest(PresenceServiceTestCase("testServiceRegistration"))
		suite.addTest(PresenceServiceTestCase("testServiceDetection"))
	addToSuite = staticmethod(addToSuite)

def runTests():
	suite = unittest.TestSuite()
	PresenceServiceTestCase.addToSuite(suite)
	runner = unittest.TextTestRunner()
	runner.run(suite)

def main():
	import pygtk, gtk
	global ps
	ps = PresenceService.get_instance()
	ps.set_debug(True)
	ps.start()
	gobject.timeout_add(4000, runTests)
	gtk.main()

if __name__ == "__main__":
	main()
