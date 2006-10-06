import avahi, dbus, dbus.glib, gobject
import Buddy
import Service
import Activity
import random
import logging
from sugar import util
import BuddyIconCache


_SA_UNRESOLVED = 0
_SA_RESOLVE_PENDING = 1
_SA_RESOLVED = 2
class ServiceAdv(object):
	"""Wrapper class to track services from Avahi."""
	def __init__(self, interface, protocol, name, stype, domain, local):
		self._interface = interface
		self._protocol = protocol
		if not isinstance(name, unicode):
			raise ValueError("service advertisement name must be unicode.")
		self._name = name
		if not isinstance(stype, unicode):
			raise ValueError("service advertisement type must be unicode.")
		self._stype = stype
		if not isinstance(domain, unicode):
			raise ValueError("service advertisement domain must be unicode.")
		self._domain = domain
		self._service = None
		if not isinstance(local, bool):
			raise ValueError("local must be a bool.")
		self._local = local
		self._state = _SA_UNRESOLVED
		self._resolver = None

	def __del__(self):
		if self._resolver:
			del self._resolver

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
	def is_local(self):
		return self._local
	def service(self):
		return self._service
	def set_service(self, service):
		if not isinstance(service, Service.Service):
			raise ValueError("must be a valid service.")
		if service != self._service:
			self._service = service
	def resolver(self):
		return self._resolver
	def set_resolver(self, resolver):
		if not isinstance(resolver, dbus.Interface):
			raise ValueError("must be a valid dbus object")
		self._resolver = resolver
	def state(self):
		return self._state
	def set_state(self, state):
		if state == _SA_RESOLVE_PENDING:
			if self._state == _SA_RESOLVED:
				raise ValueError("Can't reset to resolve pending from resolved.")
		self._state = state

class RegisteredServiceType(object):
	def __init__(self, stype):
		self._stype = stype
		self._refcount = 1

	def get_type(self):
		return self._stype

	def ref(self):
		self._refcount += 1

	def unref(self):
		self._refcount -= 1
		return self._refcount

def _txt_to_dict(txt):
	"""Convert an avahi-returned TXT record formatted
	as nested arrays of integers (from dbus) into a dict
	of key/value string pairs."""
	prop_dict = {}
	props = avahi.txt_array_to_string_array(txt)
	for item in props:
		key = value = None
		if '=' not in item:
			# No = means a boolean value of true
			key = item
			value = True
		else:
			(key, value) = item.split('=')
		prop_dict[key] = value
	return prop_dict


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
		ret = []
		for serv in self._parent.get_services():
			ret.append(serv.object_path())
		return ret

	@dbus.service.method(_PRESENCE_DBUS_INTERFACE,
						in_signature="s", out_signature="ao")
	def getServicesOfType(self, stype):
		ret = []
		for serv in self._parent.get_services_of_type(stype):
			ret.append(serv.object_path())
		return ret

	@dbus.service.method(_PRESENCE_DBUS_INTERFACE,
						in_signature="", out_signature="ao")
	def getActivities(self):
		ret = []
		for act in self._parent.get_activities():
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
		ret = []
		for buddy in self._parent.get_buddies():
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
						in_signature="os", out_signature="o",
						sender_keyword="sender")
	def joinActivity(self, activity_op, stype, sender):
		found_activity = None
		acts = self._parent.get_activities()
		for act in acts:
			if act.object_path() == activity_op:
				found_activity = act
				break
		if not found_activity:
			raise NotFoundError("The activity %s was not found." % activity_op)
		return self._parent.join_activity(found_activity, stype, sender)

	@dbus.service.method(_PRESENCE_DBUS_INTERFACE,
						in_signature="ssa{ss}sis", out_signature="o",
						sender_keyword="sender")
	def shareActivity(self, activity_id, stype, properties, address, port,
			domain, sender=None):
		if not len(address):
			address = None
		service = self._parent.share_activity(activity_id, stype, properties, address,
				port, domain, sender)
		return service.object_path()

	@dbus.service.method(_PRESENCE_DBUS_INTERFACE,
						in_signature="ssa{ss}sis", out_signature="o",
						sender_keyword="sender")
	def registerService(self, name, stype, properties, address, port, domain,
			sender=None):
		if not len(address):
			address = None
		service = self._parent.register_service(name, stype, properties, address,
				port, domain, sender)
		return service.object_path()

	@dbus.service.method(_PRESENCE_DBUS_INTERFACE,
						in_signature="o", out_signature="",
						sender_keyword="sender")
	def unregisterService(self, service_op, sender):
		found_serv = None
		services = self._parent.get_services()
		for serv in services:
			if serv.object_path() == service_op:
				found_serv = serv
				break
		if not found_serv:
			raise NotFoundError("The service %s was not found." % service_op)
		return self._parent.unregister_service(found_serv, sender)

	@dbus.service.method(_PRESENCE_DBUS_INTERFACE,
						in_signature="s", out_signature="")
	def registerServiceType(self, stype):
		self._parent.register_service_type(stype)

	@dbus.service.method(_PRESENCE_DBUS_INTERFACE,
						in_signature="s", out_signature="")
	def unregisterServiceType(self, stype):
		self._parent.unregister_service_type(stype)

	@dbus.service.method(_PRESENCE_DBUS_INTERFACE)
	def start(self):
		self._parent.start()

class PresenceService(object):
	def __init__(self):
		# interface -> IP address: interfaces we've gotten events on so far
		self._local_addrs = {}

		self._next_object_id = 0

		self._buddies = {} 		# nick -> Buddy
		self._services = {}		# (name, type) -> Service
		self._activities = {}	# activity id -> Activity

		# Keep track of stuff we're already browsing
		self._service_type_browsers = {}
		self._service_browsers = {}

		# Resolved service list
		self._service_advs = []

		# Service types we care about resolving
		self._registered_service_types = []

		# Set up the dbus service we provide
		self._session_bus = dbus.SessionBus()
		self._bus_name = dbus.service.BusName(_PRESENCE_SERVICE, bus=self._session_bus)		
		self._dbus_helper = PresenceServiceDBusHelper(self, self._bus_name)

		self._icon_cache = BuddyIconCache.BuddyIconCache()

		# Our owner object
		objid = self._get_next_object_id()
		self._owner = Buddy.Owner(self, self._bus_name, objid, self._icon_cache)
		self._buddies[self._owner.get_name()] = self._owner

		self._started = False

	def start(self):
		if self._started:
			return
		self._started = True

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
		# Only return valid activities
		ret = []
		for act in self._activities.values():
			if act.is_valid():
				ret.append(act)
		return ret

	def get_activity(self, actid):
		if self._activities.has_key(actid):
			act = self._activities[actid]
			if act.is_valid():
				return act
		return None

	def get_buddies(self):
		buddies = []
		for buddy in self._buddies.values():
			if buddy.is_valid():
				buddies.append(buddy)
		return buddies

	def get_buddy_by_name(self, name):
		if self._buddies.has_key(name):
			if self._buddies[name].is_valid():
				return self._buddies[name]
		return None

	def get_buddy_by_address(self, address):
		for buddy in self._buddies.values():
			if buddy.get_address() == address and buddy.is_valid():
				return buddy
		return None

	def get_owner(self):
		return self._owner

	def _find_service_adv(self, interface=None, protocol=None, name=None,
			stype=None, domain=None, local=None):
		"""Search a list of service advertisements for ones matching
		certain criteria."""
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
			if local is not None and adv.is_local() != local:
				continue
			adv_list.append(adv)
		return adv_list

	def _find_registered_service_type(self, stype):
		for item in self._registered_service_types:
			if item.get_type() == stype:
				return item
		return None

	def _handle_new_service_for_buddy(self, service, local):
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
			source_addr = service.get_source_address()
			objid = self._get_next_object_id()
			buddy = Buddy.Buddy(self._bus_name, objid, service, self._icon_cache)
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
		was_valid = False
		if not self._activities.has_key(actid):
			objid = self._get_next_object_id()
			activity = Activity.Activity(self._bus_name, objid, service)
			self._activities[actid] = activity
		else:
			activity = self._activities[actid]
			was_valid = activity.is_valid()

		if activity:
			activity.add_service(service)

			# Add the activity to its buddy
			# FIXME: use something other than name to attribute to buddy
			try:
				buddy = self._buddies[service.get_name()]
				buddy.add_activity(activity)
			except KeyError:
				pass		

		if not was_valid and activity.is_valid():
			self._dbus_helper.ActivityAppeared(activity.object_path())

	def _handle_remove_activity_service(self, service):
		actid = service.get_activity_id()
		if not actid:
			return
		if not self._activities.has_key(actid):
			return

		activity = self._activities[actid]

		activity.remove_service(service)
		if len(activity.get_services()) == 0:
			# Remove the activity from its buddy
			# FIXME: use something other than name to attribute to buddy
			try:
				buddy = self._buddies[service.get_name()]
				buddy.remove_activity(activity)
			except KeyError:
				pass		

			# Kill the activity
			self._dbus_helper.ActivityDisappeared(activity.object_path())
			del self._activities[actid]

	def _service_resolved_cb(self, adv, interface, protocol, full_name,
			stype, domain, host, aprotocol, address, port, txt, flags,
			updated):
		"""When the service discovery finally gets here, we've got enough
		information about the service to assign it to a buddy."""
		if updated == False:
			logging.debug("Resolved service '%s' type '%s' domain '%s' to " \
					" %s:%s" % (full_name, stype, domain, address, port))

		if not adv in self._service_advs:
			return False
		if adv.state() != _SA_RESOLVED:
			return False

		# See if we know about this service already
		service = None
		key = (full_name, stype)
		props = _txt_to_dict(txt)
		if not self._services.has_key(key):
			objid = self._get_next_object_id()
			service = Service.Service(self._bus_name, objid, name=full_name,
					stype=stype, domain=domain, address=address, port=port,
					properties=props, source_address=address)
			self._services[key] = service
		else:
			# Already tracking this service; either:
			# a) we were the one that shared it in the first place,
			#     and therefore the source address would not have
			#     been set yet
			# b) the service has been updated
			service = self._services[key]
			if not service.get_source_address():
				service.set_source_address(address)
			if not service.get_address():
				service.set_address(address)

		adv.set_service(service)

		if service and updated:
			service.set_properties(props, from_network=True)
			return False

		# Merge the service into our buddy and activity lists, if needed
		buddy = self._handle_new_service_for_buddy(service, adv.is_local())
		if buddy and service.get_activity_id():
			self._handle_new_activity_service(service)

		return False

	def _service_resolved_cb_glue(self, adv, interface, protocol, name,
			stype, domain, host, aprotocol, address, port, txt, flags):
		# Avahi doesn't flag updates to existing services, so we have
		# to determine that here
		updated = False
		if adv.state() == _SA_RESOLVED:
			updated = True

		adv.set_state(_SA_RESOLVED)
		gobject.idle_add(self._service_resolved_cb, adv, interface,
				protocol, name, stype, domain, host, aprotocol, address,
				port, txt, flags, updated)

	def _service_resolved_failure_cb(self, adv, err):
		adv.set_state(_SA_UNRESOLVED)
		logging.error("Error resolving service %s.%s: %s" % (adv.name(), adv.stype(), err))

	def _resolve_service(self, adv):
		"""Resolve and lookup a ZeroConf service to obtain its address and TXT records."""
		# Ask avahi to resolve this particular service
		path = self._mdns_service.ServiceResolverNew(dbus.Int32(adv.interface()),
				dbus.Int32(adv.protocol()), adv.name(), adv.stype(), adv.domain(),
				avahi.PROTO_UNSPEC, dbus.UInt32(0))
		resolver = dbus.Interface(self._system_bus.get_object(avahi.DBUS_NAME, path),
							avahi.DBUS_INTERFACE_SERVICE_RESOLVER)
		resolver.connect_to_signal('Found', lambda *args: self._service_resolved_cb_glue(adv, *args))
		resolver.connect_to_signal('Failure', lambda *args: self._service_resolved_failure_cb(adv, *args))
		adv.set_resolver(resolver)
		return False

	def _service_appeared_cb(self, interface, protocol, full_name, stype, domain, flags):
		local = flags & avahi.LOOKUP_RESULT_OUR_OWN > 0
		adv_list = self._find_service_adv(interface=interface, protocol=protocol,
				name=full_name, stype=stype, domain=domain, local=local)
		adv = None
		if not adv_list:
			adv = ServiceAdv(interface=interface, protocol=protocol, name=full_name,
					stype=stype, domain=domain, local=local)
			self._service_advs.append(adv)
		else:
			adv = adv_list[0]

		# Decompose service name if we can
		(actid, buddy_name) = Service.decompose_service_name(full_name)

		# If we care about the service right now, resolve it
		resolve = False
		item = self._find_registered_service_type(stype)
		if actid is not None or item is not None:
			resolve = True
		if resolve and adv.state() == _SA_UNRESOLVED:
			logging.debug("Found '%s' (%d) of type '%s' in domain" \
					" '%s' on %i.%i; will resolve." % (full_name, flags, stype,
					domain, interface, protocol))
			adv.set_state(_SA_RESOLVE_PENDING)
			gobject.idle_add(self._resolve_service, adv)
			
		return False

	def _service_appeared_cb_glue(self, interface, protocol, name, stype, domain, flags):
		gobject.idle_add(self._service_appeared_cb, interface, protocol, name, stype, domain, flags)

	def _service_disappeared_cb(self, interface, protocol, full_name, stype, domain, flags):
		local = flags & avahi.LOOKUP_RESULT_OUR_OWN > 0
		# If it's an unresolved service, remove it from our unresolved list
		adv_list = self._find_service_adv(interface=interface, protocol=protocol,
				name=full_name, stype=stype, domain=domain, local=local)
		if not adv_list:
			return False

		# Get the service object; if none, we have nothing left to do
		adv = adv_list[0]
		service = adv.service()
		self._service_advs.remove(adv)
		del adv
		if not service:
			return False

		logging.debug("Service %s.%s in domain %s on %i.%i disappeared." % (full_name,
				stype, domain, interface, protocol))

		self._dbus_helper.ServiceDisappeared(service.object_path())
		self._handle_remove_activity_service(service)

		# Decompose service name if we can
		(actid, buddy_name) = Service.decompose_service_name(full_name)

		# Remove the service from the buddy
		try:
			buddy = self._buddies[buddy_name]
		except KeyError:
			pass
		else:
			buddy.remove_service(service)
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
		try:
			s_browser = self._mdns_service.ServiceBrowserNew(interface,
					protocol, stype, domain, dbus.UInt32(0))
			browser_obj = dbus.Interface(self._system_bus.get_object(avahi.DBUS_NAME, s_browser),
							avahi.DBUS_INTERFACE_SERVICE_BROWSER)
			browser_obj.connect_to_signal('ItemNew', self._service_appeared_cb_glue)
			browser_obj.connect_to_signal('ItemRemove', self._service_disappeared_cb_glue)

			self._service_browsers[(interface, protocol, stype, domain)] = browser_obj
		except dbus.DBusException:
			logging.debug("Error browsing service type '%s'" % stype)
		return False

	def _new_service_type_cb_glue(self, interface, protocol, stype, domain, flags):
		if len(stype) > 0:
			gobject.idle_add(self._new_service_type_cb, interface, protocol,
					stype, domain, flags)

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
			str_exc = str(exc)
			logging.error("got exception %s while attempting to browse domain %s on %i.%i" % (str_exc, domain, interface, protocol))
			if str_exc.find("The name org.freedesktop.Avahi was not provided by any .service files") >= 0:
				raise Exception("Avahi does not appear to be running.  '%s'" % str_exc)
			else:
				raise exc
		logging.debug("Browsing domain '%s' on %i.%i ..." % (domain, interface, protocol))
		browser_obj.connect_to_signal('ItemNew', self._new_service_type_cb_glue)
		self._service_type_browsers[(interface, protocol, domain)] = browser_obj
		return False

	def _new_domain_cb_glue(self, interface, protocol, domain, flags=0):
		gobject.idle_add(self._new_domain_cb, interface, protocol, domain, flags)

	def join_activity(self, activity, stype, sender):
		services = activity.get_services_of_type(stype)
		if not len(services):
			raise NotFoundError("The service type %s was not present within " \
					"the activity %s" % (stype, activity.object_path()))
		act_service = services[0]
		props = act_service.get_properties()
		color = activity.get_color()
		if color:
			props['color'] = color
		return self._share_activity(activity.get_id(), stype, properties,
				act_service.get_address(), act_service.get_port(),
				act_service.get_domain(), sender)

	def share_activity(self, activity_id, stype, properties=None, address=None,
			port=-1, domain=u"local", sender=None):
		"""Convenience function to share an activity with other buddies."""
		if not util.validate_activity_id(activity_id):
			raise ValueError("invalid activity id")
		owner_nick = self._owner.get_name()
		real_name = Service.compose_service_name(owner_nick, activity_id)
		if address and not isinstance(address, unicode):
			raise ValueError("address must be a unicode string.")
		if address == None and stype.endswith('_udp'):
			# Use random currently unassigned multicast address
			address = u"232.%d.%d.%d" % (random.randint(0, 254), random.randint(1, 254),
					random.randint(1, 254))
			properties['address'] = address
			properties['port'] = port
		if port and port != -1 and (not isinstance(port, int) or port <= 1024 or port >= 65535):
			raise ValueError("port must be a number between 1024 and 65535")
		
		color = self._owner.get_color()
		if color:
			properties['color'] = color

		logging.debug('Share activity %s, type %s, address %s, port %d, " \
				"properties %s' % (activity_id, stype, address, port,
				properties))
		return self.register_service(real_name, stype, properties, address,
				port, domain, sender)

	def register_service(self, name, stype, properties={}, address=None,
			port=-1, domain=u"local", sender=None):
		"""Register a new service, advertising it to other Buddies on the network."""
		# Refuse to register if we can't get the dbus connection this request
		# came from for some reason
		if not sender:
			raise RuntimeError("Service registration request must have a sender.")

		(actid, person_name) = Service.decompose_service_name(name)
		if self.get_owner() and person_name != self.get_owner().get_name():
			raise RuntimeError("Tried to register a service that didn't have" \
					" Owner nick as the service name!")
		if not domain or not len(domain):
			domain = u"local"
		if not port or port == -1:
			port = random.randint(4000, 65000)

		objid = self._get_next_object_id()
		service = Service.Service(self._bus_name, objid, name=name,
				stype=stype, domain=domain, address=address, port=port,
				properties=properties, source_address=None,
				local_publisher=sender)
		self._services[(name, stype)] = service
		self.register_service_type(stype)
		service.register(self._system_bus, self._mdns_service)		
		return service

	def unregister_service(self, service, sender=None):
		service.unregister(sender)

	def register_service_type(self, stype):
		"""Requests that the Presence service look for and recognize
		a certain mDNS service types."""
		if not isinstance(stype, unicode):
			raise ValueError("service type must be a unicode string.")

		# If we've already registered it as a service type, ref it and return
		item = self._find_registered_service_type(stype)
		if item is not None:
			item.ref()
			return

		# Otherwise track this type now
		obj = RegisteredServiceType(stype)
		self._registered_service_types.append(obj)

		# Find unresolved services that match the service type
		# we're now interested in, and resolve them
		resolv_list = []

		# Find services of this type
		resolv_list = self._find_service_adv(stype=stype)
		# Request resolution for them if they aren't in-process already
		for adv in resolv_list:
			if adv.state() == _SA_UNRESOLVED:
				adv.set_state(_SA_RESOLVE_PENDING)
				gobject.idle_add(self._resolve_service, adv)

	def unregister_service_type(self, stype):
		"""Stop tracking a certain mDNS service."""
		if not isinstance(stype, unicode):
			raise ValueError("service type must be a unicode string.")

		# if it was found, unref it and possibly remove it
		item = self._find_registered_service_type(stype)
		if not item:
			return
		if item.unref() <= 0:
			self._registered_service_types.remove(item)
			del item


def main():
	from sugar import TracebackUtils
	loop = gobject.MainLoop()
	ps = PresenceService()
	tbh = TracebackUtils.TracebackHelper()
	try:
		loop.run()
	except KeyboardInterrupt:
		print 'Ctrl+C pressed, exiting...'

	del tbh


if __name__ == "__main__":
	main()
