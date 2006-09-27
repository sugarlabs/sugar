import base64
import logging

import gobject
import dbus, dbus.service
from sugar import env


PRESENCE_SERVICE_TYPE = "_presence_olpc._tcp"
BUDDY_DBUS_OBJECT_PATH = "/org/laptop/Presence/Buddies/"
BUDDY_DBUS_INTERFACE = "org.laptop.Presence.Buddy"

_BUDDY_KEY_COLOR = 'color'
_BUDDY_KEY_CURACT = 'curact'

class NotFoundError(Exception):
	pass

class BuddyDBusHelper(dbus.service.Object):
	def __init__(self, parent, bus_name, object_path):
		self._parent = parent
		self._bus_name = bus_name
		self._object_path = object_path
		dbus.service.Object.__init__(self, bus_name, self._object_path)

	@dbus.service.signal(BUDDY_DBUS_INTERFACE,
						signature="o")
	def ServiceAppeared(self, object_path):
		pass

	@dbus.service.signal(BUDDY_DBUS_INTERFACE,
						signature="o")
	def ServiceDisappeared(self, object_path):
		pass

	@dbus.service.signal(BUDDY_DBUS_INTERFACE,
						signature="")
	def Disappeared(self):
		pass

	@dbus.service.signal(BUDDY_DBUS_INTERFACE,
						signature="ao")
	def CurrentActivityChanged(self, activities):
		pass

	@dbus.service.signal(BUDDY_DBUS_INTERFACE,
						signature="")
	def IconChanged(self):
		pass

	@dbus.service.signal(BUDDY_DBUS_INTERFACE,
						signature="o")
	def JoinedActivity(self, object_path):
		pass

	@dbus.service.signal(BUDDY_DBUS_INTERFACE,
						signature="o")
	def LeftActivity(self, object_path):
		pass

	@dbus.service.signal(BUDDY_DBUS_INTERFACE,
						signature="as")
	def PropertyChanged(self, prop_list):
		pass

	@dbus.service.method(BUDDY_DBUS_INTERFACE,
						in_signature="", out_signature="ay")
	def getIcon(self):
		icon = self._parent.get_icon()
		if not icon:
			return ""
		return icon

	@dbus.service.method(BUDDY_DBUS_INTERFACE,
						in_signature="s", out_signature="o")
	def getServiceOfType(self, stype):
		service = self._parent.get_service_of_type(stype)
		if not service:
			raise NotFoundError("Not found")
		return service.object_path()

	@dbus.service.method(BUDDY_DBUS_INTERFACE,
						in_signature="", out_signature="ao")
	def getJoinedActivities(self):
		acts = []
		for act in self._parent.get_joined_activities():
			acts.append(act.object_path())
		return acts

	@dbus.service.method(BUDDY_DBUS_INTERFACE,
						in_signature="", out_signature="a{sv}")
	def getProperties(self):
		props = {}
		props['name'] = self._parent.get_name()
		addr = self._parent.get_address()
		if addr:
			props['ip4_address'] = addr
		props['owner'] = self._parent.is_owner()
		color = self._parent.get_color()
		if color:
			props[_BUDDY_KEY_COLOR] = self._parent.get_color()
		return props

	@dbus.service.method(BUDDY_DBUS_INTERFACE,
						in_signature="", out_signature="o")
	def getCurrentActivity(self):
		activity = self._parent.get_current_activity()
		if not activity:
			raise NotFoundError()
		return activity.object_path()

class Buddy(object):
	"""Represents another person on the network and keeps track of the
	activities and resources they make available for sharing."""

	def __init__(self, bus_name, object_id, service, icon_cache):
		if not bus_name:
			raise ValueError("DBus bus name must be valid")
		if not object_id or type(object_id) != type(1):
			raise ValueError("object id must be a valid number")
		# Normal Buddy objects must be created with a valid service,
		# owner objects do not
		if not isinstance(self, Owner):
			if not isinstance(service, Service.Service):
				raise ValueError("service must be a valid service object")

		self._services = {}
		self._activities = {}

		self._icon_cache = icon_cache

		self._nick_name = None
		self._address = None
		if service is not None:
			self._nick_name = service.get_name()
			self._address = service.get_source_address()
		self._color = None
		self._current_activity = None
		self._valid = False
		self._icon = None
		self._icon_tries = 0

		self._object_id = object_id
		self._object_path = BUDDY_DBUS_OBJECT_PATH + str(self._object_id)
		self._dbus_helper = BuddyDBusHelper(self, bus_name, self._object_path)

		self._buddy_presence_service = None
		if service is not None:
			self.add_service(service)

	def object_path(self):
		return dbus.ObjectPath(self._object_path)

	def _request_buddy_icon_cb(self, result_status, response, user_data):
		"""Callback when icon request has completed."""
		from sugar.p2p import network
		icon = response
		service = user_data
		if result_status == network.RESULT_SUCCESS:
			if icon and len(icon):
				icon = base64.b64decode(icon)
				self._set_icon(icon)
				self._icon_cache.add_icon(icon)

		if (result_status == network.RESULT_FAILED or not icon) and self._icon_tries < 3:
			self._icon_tries = self._icon_tries + 1
			if self._icon_tries >= 3:
				logging.debug("Failed to retrieve buddy icon for '%s'." % self._nick_name)
			gobject.timeout_add(1000, self._get_buddy_icon, service, True)
		return False

	def _get_buddy_icon(self, service, retry=False):
		"""Get the buddy's icon.  Check the cache first, if its
		not there get the icon from the buddy over the network."""
		if retry != True:
			# Only hit the cache once
			icon_hash = service.get_one_property('icon-hash')
			if icon_hash is not None:
				icon = self._icon_cache.get_icon(icon_hash)
				if icon:
					logging.debug("%s: icon cache hit for %s." % (self._nick_name, icon_hash))
					self._set_icon(icon)
					return False
			logging.debug("%s: icon cache miss, fetching icon from buddy..." % self._nick_name)

		from sugar.p2p import Stream
		buddy_stream = Stream.Stream.new_from_service(service, start_reader=False)
		writer = buddy_stream.new_writer(service)
		success = writer.custom_request("get_buddy_icon", self._request_buddy_icon_cb, service)
		if not success:
			del writer, buddy_stream
			gobject.timeout_add(1000, self._get_buddy_icon, service, True)
		return False

	def _get_service_key(self, service):
		return (service.get_type(), service.get_activity_id())

	def add_service(self, service):
		"""Adds a new service to this buddy's service list, returning
		True if the service was successfully added, and False if it was not."""
		if service.get_name() != self._nick_name:
			logging.error("Service and buddy nick names doesn't match: " \
					"%s %s" % (service.get_name(), self._nick_name))
			return False

		source_addr = service.get_source_address()
		if source_addr != self._address:
			logging.error("Service source and buddy address doesn't " \
					"match: %s %s" % (source_addr, self._address))
			return False		
		return self._internal_add_service(service)

	def _internal_add_service(self, service):
		service_key = self._get_service_key(service)
		if service_key in self._services.keys():
			logging.error("Service already known: %s %s" % (service_key[0],
					service_key[1]))
			return False

		if service.get_type() == PRESENCE_SERVICE_TYPE and self._buddy_presence_service:
			# already have a presence service for this buddy
			logging.debug("!!! Tried to add a buddy presence service when " \
					"one already existed.")
			return False

		logging.debug("Buddy %s added service type %s id %s" % (self._nick_name,
				service.get_type(), service.get_activity_id()))
		self._services[service_key] = service
		service.set_owner(self)

		if service.get_type() == PRESENCE_SERVICE_TYPE:
			self._buddy_presence_service = service
			# A buddy isn't valid until its official presence
			# service has been found and resolved
			self._valid = True
			self._get_buddy_icon(service)
			self._color = service.get_one_property(_BUDDY_KEY_COLOR)
			self._current_activity = service.get_one_property(_BUDDY_KEY_CURACT)
			# Monitor further buddy property changes, like current activity
			# and color
			service.connect('property-changed',
					self.__buddy_presence_service_property_changed_cb)

		if self._valid:
			self._dbus_helper.ServiceAppeared(service.object_path())
		return True

	def __buddy_presence_service_property_changed_cb(self, service, keys):
		if _BUDDY_KEY_COLOR in keys:
			new_color = service.get_one_property(_BUDDY_KEY_COLOR)
			if new_color and self._color != new_color:
				self._color = new_color
				self._dbus_helper.PropertyChanged([_BUDDY_KEY_COLOR])
		if _BUDDY_KEY_CURACT in keys:
			# Three cases here:
			# 1) Buddy didn't publish a 'curact' key at all; we do nothing
			# 2) Buddy published a blank/zero-length 'curact' key; we send
			#        a current-activity-changed signal for no activity
			# 3) Buddy published a non-zero-length 'curact' key; we send
			#        a current-activity-changed signal if we know about the
			#        activity already, if not we postpone until the activity
			#        is found on the network and added to the buddy
			new_curact = service.get_one_property(_BUDDY_KEY_CURACT)
			if new_curact and self._current_activity != new_curact:
				if not len(new_curact):
					new_curact = None
				self._current_activity = new_curact
				if self._activities.has_key(self._current_activity):
					# Case (3) above, valid activity id
					activity = self._activities[self._current_activity]
					if activity.is_valid():
						self._dbus_helper.CurrentActivityChanged([activity.object_path()])
				elif not self._current_activity:
					# Case (2) above, no current activity
					self._dbus_helper.CurrentActivityChanged([])

	def __find_service_by_activity_id(self, actid):
		for serv in self._services.values():
			if serv.get_activity_id() == actid:
				return serv
		return None

	def add_activity(self, activity):
		if activity in self._activities.values():
			return
		actid = activity.get_id()
		if not self.__find_service_by_activity_id(actid):
			raise RuntimeError("Tried to add activity for which we had no service")
		self._activities[actid] = activity
		if activity.is_valid():
			self._dbus_helper.JoinedActivity(activity.object_path())

			# If when we received a current activity update from the buddy,
			# but didn't know about that activity yet, and now we do know about
			# it, we need to send out the changed activity signal
			if actid == self._current_activity:
				self._dbus_helper.CurrentActivityChanged([activity.object_path()])

	def remove_service(self, service):
		"""Remove a service from a buddy; ie, the activity was closed
		or the buddy went away."""
		if service.get_source_address() != self._address:
			return
		if service.get_name() != self._nick_name:
			return

		if service.get_type() == PRESENCE_SERVICE_TYPE \
				and self._buddy_presence_service \
				and service != self._buddy_presence_service:
			logging.debug("!!! Tried to remove a spurious buddy presence service.")
			return

		service_key = self._get_service_key(service)
		if self._services.has_key(service_key):
			if self._valid:
				self._dbus_helper.ServiceDisappeared(service.object_path())
			del self._services[service_key]

		if service.get_type() == PRESENCE_SERVICE_TYPE:
			self._valid = False
			self._dbus_helper.Disappeared()

	def remove_activity(self, activity):
		actid = activity.get_id()
		if not self._activities.has_key(actid):
			return
		del self._activities[actid]
		if activity.is_valid():
			self._dbus_helper.LeftActivity(activity.object_path())

		# If we just removed the buddy's current activity,
		# send out a signal
		if actid == self._current_activity:
			self._current_activity = None
			self._dbus_helper.CurrentActivityChanged([])

	def get_joined_activities(self):
		acts = []
		for act in self._activities.values():
			if act.is_valid():
				acts.append(act)
		return acts

	def get_service_of_type(self, stype=None, activity=None):
		"""Return a service of a certain type, or None if the buddy
		doesn't provide that service."""
		if not stype:
			raise RuntimeError("Need to specify a service type.")

		if activity and not activity.is_valid():
			raise RuntimeError("Activity is not yet valid.")

		if activity:
			key = (stype, activity.get_id())
		else:
			key = (stype, None)
		if self._services.has_key(key):
			return self._services[key]
		return None

	def is_valid(self):
		"""Return whether the buddy is valid or not.  A buddy is
		not valid until its official presence service has been found
		and successfully resolved."""
		return self._valid

	def get_icon(self):
		"""Return the buddies icon, if any."""
		return self._icon
		
	def get_address(self):
		return self._address

	def get_name(self):
		return self._nick_name

	def get_color(self):
		return self._color

	def get_current_activity(self):
		if not self._current_activity:
			return None
		if not self._activities.has_key(self._current_activity):
			return None
		return self._activities[self._current_activity]

	def _set_icon(self, icon):
		"""Can only set icon for other buddies.  The Owner
		takes care of setting it's own icon."""
		if icon != self._icon:
			self._icon = icon
			self._dbus_helper.IconChanged()

	def is_owner(self):
		return False


class Owner(Buddy):
	"""Class representing the owner of the machine.  This is the client
	portion of the Owner, paired with the server portion in Owner.py."""
	def __init__(self, ps, bus_name, object_id, icon_cache):
		Buddy.__init__(self, bus_name, object_id, None, icon_cache)
		self._nick_name = env.get_nick_name()
		self._color = env.get_color()
		self._ps = ps

	def add_service(self, service):
		"""Adds a new service to this buddy's service list, returning
		True if the service was successfully added, and False if it was not."""
		if service.get_name() != self._nick_name:
			logging.error("Service and buddy nick names doesn't match: " \
					"%s %s" % (service.get_name(), self._nick_name))
			return False

		# The Owner initially doesn't have an address, so the first
		# service added to the Owner determines the owner's address
		source_addr = service.get_source_address()
		if self._address is None and service.is_local():
			self._address = source_addr
			self._dbus_helper.PropertyChanged(['ip4_address'])

		# The owner bypasses address checks and only cares if
		# avahi says the service is a local service
		if not service.is_local():
			logging.error("Cannot add remote service to owner object.")
			return False

		logging.debug("Adding owner service %s.%s at %s:%d." % (service.get_name(),
				service.get_type(), service.get_source_address(),
				service.get_port()))
		return self._internal_add_service(service)

	def is_owner(self):
		return True


#################################################################
# Tests
#################################################################

import unittest
import Service

__objid_seq = 0
def _next_objid():
	global __objid_seq
	__objid_seq = __objid_seq + 1
	return __objid_seq


class BuddyTestCase(unittest.TestCase):
	_DEF_NAME = u"Tommy"
	_DEF_STYPE = unicode(PRESENCE_SERVICE_TYPE)
	_DEF_DOMAIN = u"local"
	_DEF_ADDRESS = u"1.1.1.1"
	_DEF_PORT = 1234

	def __init__(self, name):
		self._bus = dbus.SessionBus()
		self._bus_name = dbus.service.BusName('org.laptop.Presence', bus=self._bus)		
		unittest.TestCase.__init__(self, name)

	def __del__(self):
		del self._bus_name
		del self._bus

	def _test_init_fail(self, service, fail_msg):
		"""Test something we expect to fail."""
		try:
			objid = _next_objid()
			buddy = Buddy(self._bus_name, objid, service, owner=False)
		except ValueError, exc:
			pass
		else:
			self.fail("expected a ValueError for %s." % fail_msg)

	def testService(self):
		service = None
		self._test_init_fail(service, "invalid service")

	def testGoodInit(self):
		objid = _next_objid()
		service = Service.Service(self._bus_name, objid, self._DEF_NAME, self._DEF_STYPE, self._DEF_DOMAIN,
				self._DEF_ADDRESS, self._DEF_PORT)
		objid = _next_objid()
		buddy = Buddy(self._bus_name, objid, service)
		assert buddy.get_name() == self._DEF_NAME, "buddy name wasn't correct after init."
		assert buddy.get_address() == self._DEF_ADDRESS, "buddy address wasn't correct after init."
		assert buddy.object_path() == BUDDY_DBUS_OBJECT_PATH + str(objid)

	def addToSuite(suite):
		suite.addTest(BuddyTestCase("testService"))
		suite.addTest(BuddyTestCase("testGoodInit"))
	addToSuite = staticmethod(addToSuite)


def main():
	suite = unittest.TestSuite()
	BuddyTestCase.addToSuite(suite)
	runner = unittest.TextTestRunner()
	runner.run(suite)

if __name__ == "__main__":
	main()
