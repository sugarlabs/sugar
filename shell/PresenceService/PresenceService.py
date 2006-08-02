import avahi, dbus, dbus.glib, gobject
import Buddy
import Service
import Activity
import random
import logging
from sugar import env
from sugar import util


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


_PRESENCE_SERVICE = "org.laptop.Presence"
_PRESENCE_DBUS_INTERFACE = "org.laptop.Presence"
_PRESENCE_OBJECT_PATH = "/org/laptop/Presence"

class NotFoundError(Exception):
	pass

class PresenceServiceDBusHelper(dbus.service.Object):
	def __init__(self, parent, bus_name):
		self._parent = parent
		self._bus_name = bus_name
		dbus.service.Object.__init__(self, bus_name, _PRESENCE_OBJECT_PATH)

	@dbus.service.signal(_PRESENCE_DBUS_INTERFACE,
						signature="o")
	def BuddyAppeared(self, object_path):
		pass

	@dbus.service.signal(_PRESENCE_DBUS_INTERFACE,
						signature="o")
	def BuddyDisappeared(self, object_path):
		pass

	@dbus.service.signal(_PRESENCE_DBUS_INTERFACE,
						signature="o")
	def ServiceAppeared(self, object_path):
		pass

	@dbus.service.signal(_PRESENCE_DBUS_INTERFACE,
						signature="o")
	def ServiceDisappeared(self, object_path):
		pass

	@dbus.service.signal(_PRESENCE_DBUS_INTERFACE,
						signature="o")
	def ActivityAppeared(self, object_path):
		pass

	@dbus.service.signal(_PRESENCE_DBUS_INTERFACE,
						signature="o")
	def ActivityDisappeared(self, object_path):
		pass

	@dbus.service.method(_PRESENCE_DBUS_INTERFACE,
						in_signature="", out_signature="ao")
	def getServices(self):
		services = self._parent.get_services()
		ret = []
		for serv in services:
			ret.append(serv.object_path())
		return ret

	@dbus.service.method(_PRESENCE_DBUS_INTERFACE,
						in_signature="s", out_signature="ao")
	def getServicesOfType(self, stype):
		services = self._parent.get_services_of_type(stype)
		ret = []
		for serv in services:
			ret.append(serv.object_path())
		return ret

	@dbus.service.method(_PRESENCE_DBUS_INTERFACE,
						in_signature="", out_signature="ao")
	def getActivities(self):
		activities = self._parent.get_activities()
		ret = []
		for act in activities:
			ret.append(act.object_path())
		return ret

	@dbus.service.method(_PRESENCE_DBUS_INTERFACE,
						in_signature="s", out_signature="o")
	def getActivity(self, actid):
		act = self._parent.get_activity(actid)
		if not act:
			raise NotFoundError("Not found")
		return act.object_path()

	@dbus.service.method(_PRESENCE_DBUS_INTERFACE,
						in_signature="", out_signature="ao")
	def getBuddies(self):
		buddies = self._parent.get_buddies()
		ret = []
		for buddy in buddies:
			ret.append(buddy.object_path())
		return ret

	@dbus.service.method(_PRESENCE_DBUS_INTERFACE,
						in_signature="s", out_signature="o")
	def getBuddyByName(self, name):
		buddy = self._parent.get_buddy_by_name(name)
		if not buddy:
			raise NotFoundError("Not found")
		return buddy.object_path()

	@dbus.service.method(_PRESENCE_DBUS_INTERFACE,
						in_signature="s", out_signature="o")
	def getBuddyByAddress(self, addr):
		buddy = self._parent.get_buddy_by_address(addr)
		if not buddy:
			raise NotFoundError("Not found")
		return buddy.object_path()

	@dbus.service.method(_PRESENCE_DBUS_INTERFACE,
						in_signature="", out_signature="o")
	def getOwner(self):
		owner = self._parent.get_owner()
		if not owner:
			raise NotFoundError("Not found")
		return owner.object_path()

	@dbus.service.method(_PRESENCE_DBUS_INTERFACE,
						in_signature="os", out_signature="o")
	def joinActivity(self, activity_op, stype):
		found_activity = None
		acts = self._parent.get_activities()
		for act in acts:
			if act.object_path() == activity_op:
				found_activity = act
				break
		if not found_activity:
			raise NotFoundError("The activity %s was not found." % activity_op)
		return self._parent.join_activity(found_activity, stype)

	@dbus.service.method(_PRESENCE_DBUS_INTERFACE,
						in_signature="ssa{ss}sis", out_signature="o")
	def shareActivity(self, activity_id, stype, properties, address, port, domain):
		if not len(address):
			address = None
		service = self._parent.share_activity(activity_id, stype, properties, address,
				port, domain)
		return service.object_path()

	@dbus.service.method(_PRESENCE_DBUS_INTERFACE,
						in_signature="ssa{ss}sis", out_signature="o")
	def registerService(self, name, stype, properties, address, port, domain):
		if not len(address):
			address = None
		service = self._parent.register_service(name, stype, properties, address,
				port, domain)
		return service.object_path()

	@dbus.service.method(_PRESENCE_DBUS_INTERFACE,
						in_signature="o", out_signature="")
	def unregisterService(self, service_op):
		found_serv = None
		serv = self._parent.get_services()
		for serv in services:
			if serv.object_path() == service_op:
				found_serv = serv
				break
		if not found_serv:
			raise NotFoundError("The activity %s was not found." % service_op)
		return self._parent.unregister_service(found_serv)

	@dbus.service.method(_PRESENCE_DBUS_INTERFACE,
						in_signature="s", out_signature="")
	def registerServiceType(self, stype):
		self._parent.register_service_type(stype)

	@dbus.service.method(_PRESENCE_DBUS_INTERFACE,
						in_signature="s", out_signature="")
	def unregisterServiceType(self, stype):
		self._parent.unregister_service_type(stype)


class PresenceService(object):
	def __init__(self):
		# interface -> IP address: interfaces we've gotten events on so far
		self._local_addrs = {}

		self._next_object_id = 0

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

		# Service types we care about resolving
		self._registered_service_types = []

		# Set up the dbus service we provide
		self._session_bus = dbus.SessionBus()
		self._bus_name = dbus.service.BusName(_PRESENCE_SERVICE, bus=self._session_bus)		
		self._dbus_helper = PresenceServiceDBusHelper(self, self._bus_name)

		# Connect to Avahi for mDNS stuff
		self._system_bus = dbus.SystemBus()
		self._mdns_service = dbus.Interface(self._system_bus.get_object(avahi.DBUS_NAME,
				avahi.DBUS_PATH_SERVER), avahi.DBUS_INTERFACE_SERVER)

		# Always browse .local
		self._new_domain_cb(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC, "local")

		# Connect to Avahi and start looking for stuff
		domain_browser = self._mdns_service.DomainBrowserNew(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC,
						"", avahi.DOMAIN_BROWSER_BROWSE, dbus.UInt32(0))
		db = dbus.Interface(self._system_bus.get_object(avahi.DBUS_NAME, domain_browser), avahi.DBUS_INTERFACE_DOMAIN_BROWSER)
		db.connect_to_signal('ItemNew', self._new_domain_cb_glue)

	def _get_next_object_id(self):
		"""Increment and return the object ID counter."""
		self._next_object_id = self._next_object_id + 1
		return self._next_object_id

	def get_services(self):
		return self._services.values()

	def get_services_of_type(self, stype):
		ret = []
		for serv in self._services.values():
			if serv.get_type() == stype:
				ret.append(serv)
		return ret

	def get_activities(self):
		return self._activities.values()

	def get_activity(self, actid):
		if self._activities.has_key(actid):
			return self._activities[actid]
		return None

	def get_buddies(self):
		return self._buddies.values()

	def get_buddy_by_name(self, name):
		if self._buddies.has_key(name):
			return self._buddies[name]
		return None

	def get_buddy_by_address(self, address):
		for buddy in self._buddies.values():
			if buddy.get_address() == address:
				return buddy
		return None

	def get_owner(self):
		return self._owner

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
				self._dbus_helper.ServiceAppeared(service.object_path())
		except KeyError:
			# Should this service mark the owner?
			owner_nick = env.get_nick_name()
			source_addr = service.get_source_address()
			objid = self._get_next_object_id()
			if name == owner_nick and source_addr in self._local_addrs.values():
				buddy = Buddy.Owner(self._bus_name, objid, service)
				self._owner = buddy
				logging.debug("Owner is '%s'." % name)
			else:
				buddy = Buddy.Buddy(self._bus_name, objid, service)
			self._buddies[name] = buddy
			self._dbus_helper.ServiceAppeared(service.object_path())
		if not buddy_was_valid and buddy.is_valid():
			self._dbus_helper.BuddyAppeared(buddy.object_path())
		return buddy

	def _handle_new_activity_service(self, service):
		# If the serivce is an activity service, merge it into our activities list
		actid = service.get_activity_id()
		if not actid:
			return
		activity = None
		if not self._activities.has_key(actid):
			objid = self._get_next_object_id()
			activity = Activity.Activity(self._bus_name, objid, service)
			self._activities[actid] = activity
			self._dbus_helper.ActivityAppeared(activity.object_path())
		else:
			activity = self._activities[actid]

		if activity:
			activity.add_service(service)

	def _handle_remove_activity_service(self, service):
		actid = service.get_activity_id()
		if not actid:
			return
		if not self._activities.has_key(actid):
			return
		activity = self._activities[actid]
		activity.remove_service(service)
		if len(activity.get_services()) == 0:
			# Kill the activity
			self._dbus_helper.ActivityDisappeared(activity.object_path())
			del self._activities[actid]

	def _resolve_service_reply_cb(self, interface, protocol, full_name, stype, domain, host, aprotocol, address, port, txt, flags):
		"""When the service discovery finally gets here, we've got enough information about the
		service to assign it to a buddy."""
		logging.debug("resolved service '%s' type '%s' domain '%s' to %s:%s" % (full_name, stype, domain, address, port))

		# If this service was previously unresolved, remove it from the
		# unresolved list
		adv_list = self._find_service_adv(interface=interface, protocol=protocol,
				name=full_name, stype=stype, domain=domain)
		if not adv_list:
			return False
		adv = adv_list[0]
		adv.set_resolved(True)
		if adv in self._resolve_queue:
			self._resolve_queue.remove(adv)

		# See if we know about this service already
		key = (full_name, stype)
		if not self._services.has_key(key):
			objid = self._get_next_object_id()
			service = Service.Service(self._bus_name, objid, name=full_name,
					stype=stype, domain=domain, address=address, port=port,
					properties=txt, source_address=address)
			self._services[key] = service
		else:
			# Already tracking this service; likely we were the one that shared it
			# in the first place, and therefore the source address would have been
			# set yet
			service = self._services[key]
			if not service.get_source_address():
				service.set_source_address(address)
			if not service.get_address():
				service.set_address(address)
		adv.set_service(service)

		# Merge the service into our buddy and activity lists, if needed
		buddy = self._handle_new_service_for_buddy(service)
		if buddy and service.get_activity_id():
			self._handle_new_activity_service(service)

		return False

	def _resolve_service_reply_cb_glue(self, interface, protocol, name, stype, domain, host, aprotocol, address, port, txt, flags):
		gobject.idle_add(self._resolve_service_reply_cb, interface, protocol,
				name, stype, domain, host, aprotocol, address, port, txt, flags)

	def _resolve_service_error_handler(self, err):
		logging.error("error resolving service: %s" % err)

	def _resolve_service(self, adv):
		"""Resolve and lookup a ZeroConf service to obtain its address and TXT records."""
		# Ask avahi to resolve this particular service
		logging.debug('resolving service %s %s' % (adv.name(), adv.stype()))
		self._mdns_service.ResolveService(int(adv.interface()), int(adv.protocol()), adv.name(),
				adv.stype(), adv.domain(), avahi.PROTO_UNSPEC, dbus.UInt32(0),
				reply_handler=self._resolve_service_reply_cb_glue,
				error_handler=self._resolve_service_error_handler)
		return False

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
			ifname = self._mdns_service.GetNetworkInterfaceNameByIndex(interface)
			if ifname:
				addr = _get_local_ip_address(ifname)
				if addr:
					self._local_addrs[interface] = addr

		# Decompose service name if we can
		(actid, buddy_name) = Service.decompose_service_name(full_name)

		# If we care about the service right now, resolve it
		resolve = False
		if actid is not None or stype in self._registered_service_types:
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
		(actid, buddy_name) = Service.decompose_service_name(full_name)

		# Remove the service from the buddy
		try:
			buddy = self._buddies[buddy_name]
		except KeyError:
			pass
		else:
			buddy.remove_service(service)
			self._dbus_helper.ServiceDisappeared(service.object_path())
			self._handle_remove_activity_service(service)
			if not buddy.is_valid():
				self._dbus_helper.BuddyDisappeared(buddy.object_path())
				del self._buddies[buddy_name]
		key = (service.get_full_name(), service.get_type())
		del self._services[key]
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

	def join_activity(self, activity, stype):
		services = activity.get_services_of_type(stype)
		if not len(services):
			raise NotFoundError("The service type %s was not present within the activity %s" % (stype, activity.object_path()))
		act_service = services[0]
		return self._share_activity(activity.get_id(), stype, act_service.get_properties(),
				act_service.get_address(), act_service.get_port(), act_service.get_domain())

	def share_activity(self, activity_id, stype, properties=None, address=None, port=-1, domain=u"local"):
		"""Convenience function to share an activity with other buddies."""
		if not util.validate_activity_id(activity_id):
			raise ValueError("invalid activity id")
		owner_nick = self._owner.get_name()
		real_name = Service.compose_service_name(owner_nick, activity_id)
		if address and type(address) != type(u""):
			raise ValueError("address must be a unicode string.")
		if address == None and stype.endswith('_udp'):
			# Use random currently unassigned multicast address
			address = u"232.%d.%d.%d" % (random.randint(0, 254), random.randint(1, 254),
					random.randint(1, 254))
			properties['address'] = address
			properties['port'] = port
		if port and port != -1 and (type(port) != type(1) or port <= 1024 or port >= 65535):
			raise ValueError("port must be a number between 1024 and 65535")

		logging.debug('Share activity %s, type %s, address %s, port %d, properties %s' % (activity_id, stype, address, port, properties))
		return self.register_service(real_name, stype, properties, address, port, domain)

	def register_service(self, name, stype, properties={}, address=None, port=-1, domain=u"local"):
		"""Register a new service, advertising it to other Buddies on the network."""
		(actid, person_name) = Service.decompose_service_name(name)
		if self.get_owner() and person_name != self.get_owner().get_name():
			raise RuntimeError("Tried to register a service that didn't have Owner nick as the service name!")
		if not domain or not len(domain):
			domain = u"local"
		if not port or port == -1:
			port = random.randint(4000, 65000)

		try:
			obj = self._system_bus.get_object(avahi.DBUS_NAME, self._mdns_service.EntryGroupNew())
			group = dbus.Interface(obj, avahi.DBUS_INTERFACE_ENTRY_GROUP)

			# Add properties; ensure they are converted to ByteArray types
			# because python sometimes can't figure that out
			info = dbus.Array([], signature="ab")
			for k, v in properties.items():
				info.append(dbus.types.ByteArray("%s=%s" % (k, v)))

			objid = self._get_next_object_id()
			service = Service.Service(self._bus_name, objid, name=name,
					stype=stype, domain=domain, address=address, port=port,
					properties=properties, source_address=None)
			self._services[(name, stype)] = service
			port = service.get_port()

			logging.debug("PS: Will register service with name='%s', stype='%s'," \
					" domain='%s', address='%s', port=%d, info='%s'" % (name, stype, domain, address, port, info))
			group.AddService(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC, 0, dbus.String(name),
					dbus.String(stype), dbus.String(domain), dbus.String(""), # let Avahi figure the 'host' out
					dbus.UInt16(port), info)
			service.set_avahi_entry_group(group)
			group.Commit()
		except dbus.exceptions.DBusException, exc:
			# FIXME: ignore local name collisions, since that means
			# the zeroconf service is already registered.  Ideally we
			# should un-register it an re-register with the correct info
			if str(exc) == "Local name collision":
				pass
		self.register_service_type(stype)
		return service

	def unregister_service(self, service):
		group = service.get_avahi_entry_group()
		if not group:
			raise ValueError("Service was not a local service provided by this laptop!")
		group.Free()
		key = (service.get_full_name(), service.get_type())
		del self._services[key]

	def register_service_type(self, stype):
		"""Requests that the Presence service look for and recognize
		a certain mDNS service types."""
		if type(stype) != type(u""):
			raise ValueError("service type must be a unicode string.")
		if stype in self._registered_service_types:
			return
		self._registered_service_types.append(stype)

		# Find unresolved services that match the service type
		# we're now interested in, and resolve them
		resolv_list = []

		# Find services of this type
		resolv_list = self._find_service_adv(stype=stype)
		# Request resolution for them if they aren't in-process already
		for adv in resolv_list:
			if adv not in self._resolve_queue:
				self._resolve_queue.append(adv)
				gobject.idle_add(self._resolve_service, adv)

	def unregister_service_type(self, stype):
		"""Stop tracking a certain mDNS service."""
		if type(stype) != type(u""):
			raise ValueError("service type must be a unicode string.")
		if stype in self._registered_service_types:
			self._registered_service_types.remove(stype)



def main():
	loop = gobject.MainLoop()
	ps = PresenceService()
	loop.run()

if __name__ == "__main__":
	main()
