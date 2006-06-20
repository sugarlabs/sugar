import threading
import avahi, dbus, dbus.glib, dbus.dbus_bindings, gobject
import Buddy
import Service
import os
import string
import random
import logging
from sugar import util
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
	"""Wrapper class for service attributes that Avahi passes back."""
	def __init__(self, interface, protocol, name, stype, domain):
		self._interface = interface
		self._protocol = protocol
		self._name = name
		self._stype = stype
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


class PresenceService(gobject.GObject):
	"""Object providing information about the presence of Buddies
	and what activities they make available to others."""

	__gsignals__ = {
		'buddy-appeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						([gobject.TYPE_PYOBJECT])),
		'buddy-disappeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						([gobject.TYPE_PYOBJECT])),
		'service-appeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT])),
		'service-disappeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT])),
		'activity-announced': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT])),
		'new-service-adv': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						([gobject.TYPE_STRING, gobject.TYPE_STRING]))
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

	def __init__(self, debug=True):
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

		# activity UID -> Service: services grouped by activity UID
		self._activity_services = {}

		# All the mdns service types we care about
		self._allowed_service_types = []  # Short service type

		# Keep track of stuff we're already browsing with ZC
		self._service_type_browsers = {}
		self._service_browsers = {}
		self._resolve_queue = [] # Track resolve requests

		# Resolved service list
		self._service_advs = []

		self._bus = dbus.SystemBus()
		self._server = dbus.Interface(self._bus.get_object(avahi.DBUS_NAME,
				avahi.DBUS_PATH_SERVER), avahi.DBUS_INTERFACE_SERVER)

	def get_activity_service(self, activity, short_stype):
		"""Find a particular service by activity and service type."""
		# Decompose service type if we can
		(uid, dec_stype) = Service._decompose_service_type(short_stype)
		if uid:
			raise RuntimeError("Can only track plain service types!")

		uid = activity.get_id()
		if self._activity_services.has_key(uid):
			services = self._activity_services[uid]
			for service in services:
				if service.get_type() == short_stype:
					return service
		return None

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

	def get_owner(self):
		"""Return the owner of this machine/instance, if we've recognized them yet."""
		return self._owner

	def _resolve_service_error_handler(self, err):
		logging.error("error resolving service: %s" % err)

	def _find_service_adv(self, interface=None, protocol=None, name=None, stype=None, domain=None, is_short_stype=False):
		"""Search a list of service advertisements for ones matching certain criteria."""
		adv_list = []
		for adv in self._service_advs:
			if interface and adv.interface() != interface:
				continue
			if protocol and adv.protocol() != protocol:
				continue
			if name and adv.name() != name:
				continue
			if is_short_stype:
				(uid, dec_stype) = Service._decompose_service_type(adv.stype())
				if uid is None or stype != dec_stype:
					continue
			else:
				if stype and adv.stype() != stype:
					continue
			if domain and adv.domain() != domain:
				continue
			adv_list.append(adv)
		return adv_list

	def _is_special_service_type(self, stype):
		"""Return True if the service type is a special, internal service
		type, and False if it's not."""
		if stype == Buddy.PRESENCE_SERVICE_TYPE:
			return True
		return False

	def _handle_new_service_for_buddy(self, service):
		"""Deal with a new discovered service object."""
		# Once a service is resolved, we match it up to an existing buddy,
		# or create a new Buddy if this is the first service known about the buddy
		buddy_was_valid = False
		name = service.get_name()
		buddy = None
		try:
			buddy = self._buddies[name]
			buddy_was_valid = buddy.is_valid()
			service_added = buddy.add_service(service)
			if service_added:
				self.emit('service-appeared', buddy, service)
		except KeyError:
			# Should this service mark the owner?
			owner_nick = env.get_nick_name()
			publisher_addr = service.get_publisher_address()
			if name == owner_nick and publisher_addr in self._local_addrs.values():
				buddy = Buddy.Owner(service)
				self._owner = buddy
				logging.debug("Owner is '%s'." % name)
			else:
				buddy = Buddy.Buddy(service)
			self._buddies[name] = buddy
			self.emit('service-appeared', buddy, service)
		if not buddy_was_valid and buddy.is_valid():
			self.emit("buddy-appeared", buddy)
		return buddy

	def _handle_new_service_for_activity(self, service, buddy):
		# If the serivce is a group service, merge it into our groups list
		uid = service.get_activity_uid()
		if not uid:
			uid = "*"
		if not self._activity_services.has_key(uid):
			self._activity_services[uid] = []
		self._activity_services[uid].append((buddy, service))
		self.emit('activity-announced', service, buddy)

	def _handle_remove_service_for_activity(self, service, buddy):
		uid = service.get_activity_uid()
		if not uid:
			uid = "*"
		if self._activity_services.has_key(uid):
			try:
				self._activity_services.remove((buddy, service))
			except:
				pass

	def _resolve_service_reply_cb(self, interface, protocol, name, full_stype, domain, host, aprotocol, address, port, txt, flags):
		"""When the service discovery finally gets here, we've got enough information about the
		service to assign it to a buddy."""
		logging.debug("resolved service '%s' type '%s' domain '%s' to %s:%s" % (name, full_stype, domain, address, port))

		name = name.encode()
		full_stype = full_stype.encode()
		domain = domain.encode()
		host = host.encode()
		address = address.encode()

		# If this service was previously unresolved, remove it from the
		# unresolved list
		adv_list = self._find_service_adv(interface=interface, protocol=protocol,
				name=name, stype=full_stype, domain=domain)
		if not adv_list:
			return False
		adv = adv_list[0]
		adv.set_resolved(True)
		if adv in self._resolve_queue:
			self._resolve_queue.remove(adv)

		# Update the service now that it's been resolved
		service = Service.Service(name=name, stype=full_stype, domain=domain,
				address=address, port=port, properties=txt)
		adv.set_service(service)

		# Merge the service into our buddy and group lists, if needed
		buddy = self._handle_new_service_for_buddy(service)
		uid = service.get_activity_uid()
		if buddy and uid:
			self._handle_new_service_for_activity(service, buddy)

		return False

	def _resolve_service_reply_cb_glue(self, interface, protocol, name, stype, domain, host, aprotocol, address, port, txt, flags):
		gobject.idle_add(self._resolve_service_reply_cb, interface, protocol,
				name, stype, domain, host, aprotocol, address, port, txt, flags)

	def _resolve_service(self, adv):
		"""Resolve and lookup a ZeroConf service to obtain its address and TXT records."""
		# Ask avahi to resolve this particular service
		logging.debug('resolving service %s %s' % (adv.name(), adv.stype()))
		self._server.ResolveService(int(adv.interface()), int(adv.protocol()), adv.name(),
				adv.stype(), adv.domain(), avahi.PROTO_UNSPEC, dbus.UInt32(0),
				reply_handler=self._resolve_service_reply_cb_glue,
				error_handler=self._resolve_service_error_handler)
		return False

	def _service_appeared_cb(self, interface, protocol, name, full_stype, domain, flags):
		logging.debug("found service '%s' (%d) of type '%s' in domain '%s' on %i.%i." % (name, flags, full_stype, domain, interface, protocol))

		# Add the service to our unresolved services list
		adv_list = self._find_service_adv(interface=interface, protocol=protocol,
				name=name.encode(), stype=full_stype.encode(), domain=domain.encode())
		adv = None
		if not adv_list:
			adv = ServiceAdv(interface=interface, protocol=protocol, name=name.encode(),
					stype=full_stype.encode(), domain=domain.encode())
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

		# Decompose service type if we can
		(uid, short_stype) = Service._decompose_service_type(full_stype.encode())

		# FIXME: find a better way of letting the StartPage get everything
		self.emit('new-service-adv', uid, short_stype)

		# If we care about the service right now, resolve it
		resolve = False
		if uid is not None or short_stype in self._allowed_service_types:
			resolve = True
		if self._is_special_service_type(short_stype):
			resolve = True
		if resolve and not adv in self._resolve_queue:
			self._resolve_queue.append(adv)
			gobject.idle_add(self._resolve_service, adv)
		else:
			logging.debug("Do not resolve service '%s' of type '%s', we don't care about it." % (name, full_stype))
			
		return False

	def _service_appeared_cb_glue(self, interface, protocol, name, stype, domain, flags):
		gobject.idle_add(self._service_appeared_cb, interface, protocol, name, stype, domain, flags)

	def _service_disappeared_cb(self, interface, protocol, name, full_stype, domain, flags):
		logging.debug("service '%s' of type '%s' in domain '%s' on %i.%i disappeared." % (name, full_stype, domain, interface, protocol))
		name = name.encode()
		full_stype = full_stype.encode()
		domain = domain.encode()

		# If it's an unresolved service, remove it from our unresolved list
		adv_list = self._find_service_adv(interface=interface, protocol=protocol,
				name=name, stype=full_stype, domain=domain)
		if not adv_list:
			return False

		# Get the service object; if none, we have nothing left to do
		adv = adv_list[0]
		if adv in self._resolve_queue:
			self._resolve_queue.remove(adv)
		service = adv.service()
		if not service:
			return False

		# Remove the service from the buddy
		try:
			buddy = self._buddies[name]
		except KeyError:
			pass
		else:
			buddy.remove_service(service)
			self.emit('service-disappeared', buddy, service)
			if not buddy.is_valid():
				self.emit("buddy-disappeared", buddy)
				del self._buddies[name]
			self._handle_remove_service_for_activity(service, buddy)

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
			st_browser = self._server.ServiceTypeBrowserNew(interface, protocol, domain, dbus.UInt32(0))
			browser_obj = dbus.Interface(self._bus.get_object(avahi.DBUS_NAME, st_browser), avahi.DBUS_INTERFACE_SERVICE_TYPE_BROWSER)
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

	def track_service_type(self, short_stype):
		"""Requests that the Presence service look for and recognize
		a certain mDNS service types."""
		if not self._started:
			raise RuntimeError("presence service must be started first.")
		if type(short_stype) == type(u""):
			raise ValueError("service type should not be unicode.")
		if type(short_stype) != type(""):
			raise ValueError("service type must be a string.")
		if self._is_special_service_type(short_stype):
			return
		if short_stype in self._allowed_service_types:
			return

		# Decompose service type if we can
		(uid, dec_stype) = Service._decompose_service_type(short_stype)
		if uid:
			raise RuntimeError("Can only track plain service types!")
		self._allowed_service_types.append(dec_stype)
		self._check_and_resolve_service_advs(dec_stype)

	def _check_and_resolve_service_advs(self, short_stype):
		"""We should only get called with short service types (ie, not
		service types that can be decomposed into a UID and a type)."""
		# Find unresolved services that match the service type
		# we're now interested in, and resolve them
		resolv_list = []

		# Find services of this type belonging to specific activities
		resolv_list = self._find_service_adv(stype=short_stype, is_short_stype=True)
		# And also just plain ones of this type
		resolv_list = resolv_list + self._find_service_adv(stype=short_stype)

		# Request resolution for them if they aren't in-process already
		for adv in resolv_list:
			if adv not in self._resolve_queue:
				self._resolve_queue.append(adv)
				gobject.idle_add(self._resolve_service, adv)

	def untrack_service_type(self, short_stype):
		"""Stop tracking a certain mDNS service."""
		if not self._started:
			raise RuntimeError("presence service must be started first.")
		if type(short_stype) == type(u""):
			raise ValueError("service type should not be unicode.")
		if not type(short_stype) == type(""):
			raise ValueError("service type must be a string.")

		# Decompose service type if we can
		(uid, dec_stype) = Service._decompose_service_type(short_stype)
		if uid:
			raise RuntimeError("Can only untrack plain service types!")

		if dec_stype in self._allowed_service_types:
			self._allowed_service_types.remove(dec_stype)

	def join_shared_activity(self, service):
		"""Convenience function to join a group and notify other buddies
		that you are a member of it."""
		if not isinstance(service, Service.Service):
			raise ValueError("service was not a valid service object.")
		self.register_service(service)

	def share_activity(self, activity, stype, properties=None, address=None, port=None):
		"""Convenience function to share an activity with other buddies."""
		if not self._started:
			raise RuntimeError("presence service must be started first.")
		uid = activity.get_id()
		owner_nick = self._owner.get_nick_name()
		real_stype = Service.compose_service_type(stype, uid)
		if address and type(address) != type(""):
			raise ValueError("address must be a valid string.")
		if address == None:
			# Use random currently unassigned multicast address
			address = "232.%d.%d.%d" % (random.randint(0, 254), random.randint(1, 254),
					random.randint(1, 254))
		if port and (type(port) != type(1) or port <= 1024 or port >= 65535):
			raise ValueError("port must be a number between 1024 and 65535")
		if not port:
			# random port #
			port = random.randint(5000, 65535)

		logging.debug('Share activity %s, type %s, address %s, port %d, properties %s' % (uid, stype, address, port, properties))
		service = Service.Service(name=owner_nick, stype=real_stype, domain="local",
				address=address, port=port, properties=properties)
		# Publish it to the world
		self.register_service(service)
		return service

	def register_service(self, service):
		"""Register a new service, advertising it to other Buddies on the network."""
		if not self._started:
			raise RuntimeError("presence service must be started first.")

		rs_name = service.get_name()
		if self.get_owner() and rs_name != self.get_owner().get_nick_name():
			raise RuntimeError("Tried to register a service that didn't have Owner nick as the service name!")
		rs_stype = service.get_full_type()
		rs_port = service.get_port()
		rs_props = service.get_properties()
		rs_domain = service.get_domain()
		rs_address = service.get_address()
		if not rs_domain or not len(rs_domain):
			rs_domain = ""
		logging.debug("registered service name '%s' type '%s' on port %d with args %s" % (rs_name, rs_stype, rs_port, rs_props))

		try:
			group = dbus.Interface(self._bus.get_object(avahi.DBUS_NAME, self._server.EntryGroupNew()), avahi.DBUS_INTERFACE_ENTRY_GROUP)

			# Add properties; ensure they are converted to ByteArray types
			# because python sometimes can't figure that out
			info = []
			for k, v in rs_props.items():
				tmp_item = "%s=%s" % (k, v)
				# Convert to local encoding for consistency (for now)
				if type(tmp_item) == type(u""):
					tmp_item = tmp_item.encode()
				info.append(dbus.types.ByteArray(tmp_item))

			if rs_address and len(rs_address):
				info.append("address=%s" % (rs_address))
			logging.debug("PS: about to call AddService for Avahi with rs_name='%s' (%s), rs_stype='%s' (%s)," \
					" rs_domain='%s' (%s), rs_port=%d (%s), info='%s' (%s)" % (rs_name, type(rs_name), rs_stype,
					type(rs_stype), rs_domain, type(rs_domain), rs_port, type(rs_port), info, type(info)))
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
		activity_stype = service.get_type()
		self.track_service_type(activity_stype)
		return group

	def get_buddy_by_nick_name(self, nick_name):
		"""Look up and return a buddy by nickname."""
		if self._buddies.has_key(nick_name):
			return self._buddies[nick_name]
		return None

	def get_buddy_by_address(self, address):
		for buddy in self._buddies.values():
			if buddy.get_address() == address:
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
