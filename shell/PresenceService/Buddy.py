import base64
import logging

import gtk
import gobject
import dbus, dbus.service


PRESENCE_SERVICE_TYPE = "_presence_olpc._tcp"
BUDDY_DBUS_INTERFACE = "org.laptop.Presence.Buddy"

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

	@dbus.service.method(BUDDY_DBUS_INTERFACE,
						in_signature="", out_signature="ay")
	def getIcon(self):
		icon = self._parent.get_icon()
		if not icon:
			return ""
		return icon

	@dbus.service.method(BUDDY_DBUS_INTERFACE,
						in_signature="", out_signature="o")
	def getServiceOfType(self, stype):
		service = self._parent.get_service_of_type(stype)
		if not service:
			raise NotFoundError("Not found")
		return service

	@dbus.service.method(BUDDY_DBUS_INTERFACE,
						in_signature="", out_signature="ao")
	def getJoinedActivities(self):
		acts = []
		return acts

	@dbus.service.method(BUDDY_DBUS_INTERFACE,
						in_signature="", out_signature="a{sv}")
	def getProperties(self):
		props = {}
		props['name'] = self._parent.get_nick_name()
		props['ip4_address'] = self._parent.get_address()
		props['owner'] = self._parent.is_owner()
		return props


class Buddy(object):
	"""Represents another person on the network and keeps track of the
	activities and resources they make available for sharing."""

	def __init__(self, bus_name, object_id, service, owner=False):
		if not bus_name:
			raise ValueError("DBus bus name must be valid")
		if not object_id or type(object_id) != type(1):
			raise ValueError("object id must be a valid number")

		self._services = {}
		self._activities = {}

		self._nick_name = service.get_name()
		self._address = service.get_publisher_address()
		self._valid = False
		self._icon = None
		self._icon_tries = 0
		self._owner = owner

		self._object_id = object_id
		self._object_path = "/org/laptop/Presence/Buddies/%d" % self._object_id
		self._dbus_helper = BuddyDBusHelper(self, bus_name, self._object_path)

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
				print "Buddy icon for '%s' is size %d" % (self._nick_name, len(icon))
				self._set_icon(icon)

		if (result_status == network.RESULT_FAILED or not icon) and self._icon_tries < 3:
			self._icon_tries = self._icon_tries + 1
			print "Failed to retrieve buddy icon for '%s' on try %d of %d" % (self._nick_name, \
					self._icon_tries, 3)
			gobject.timeout_add(1000, self._request_buddy_icon, service)
		return False

	def _request_buddy_icon(self, service):
		"""Contact the buddy to retrieve the buddy icon."""
		from sugar.p2p import Stream
		buddy_stream = Stream.Stream.new_from_service(service, start_reader=False)
		writer = buddy_stream.new_writer(service)
		success = writer.custom_request("get_buddy_icon", self._request_buddy_icon_cb, service)
		if not success:
			del writer, buddy_stream
			gobject.timeout_add(1000, self._request_buddy_icon, service)
		return False

	def add_service(self, service):
		"""Adds a new service to this buddy's service list, returning
		True if the service was successfully added, and False if it was not."""
		if service.get_name() != self._nick_name:
			return False
		publisher_addr = service.get_publisher_address()
		if publisher_addr != self._address:
			logging.error('Service publisher and buddy address doesnt match: %s %s' % (publisher_addr, self._address))
			return False
		stype = service.get_type()
		if stype in self._services.keys():
			return False
		self._services[stype] = service
		service.set_owner(self)

		if stype == PRESENCE_SERVICE_TYPE:
			# A buddy isn't valid until its official presence
			# service has been found and resolved
			self._valid = True
			print 'Requesting buddy icon %s' % self._nick_name
			self._request_buddy_icon(service)

		if self._valid:
			self._dbus_helper.ServiceAppeared(service.object_path())
		return True

	def add_activity(self, activity):
		actid = activity.get_id()
		if activity in self._activities.values():
			raise RuntimeError("Tried to add activity twice")
		found = False
		for serv in self._services.values():
			if serv.get_activity_id() == activity.get_id():
				found = True
				break
		if not found:
			raise RuntimeError("Tried to add activity for which we had no service")
		self._activities[actid] = activity
		print "Buddy (%s) joined activity %s." % (self._nick_name, actid)
		self._dbus_helper.JoinedActivity(activity.object_path())

	def remove_service(self, service):
		"""Remove a service from a buddy; ie, the activity was closed
		or the buddy went away."""
		if service.get_publisher_address() != self._address:
			return
		if service.get_name() != self._nick_name:
			return
		stype = service.get_type()
		if self._services.has_key(stype):
			if self._valid:
				self._dbus_helper.ServiceDisappeared(service.object_path())
			del self._services[stype]

		if stype == PRESENCE_SERVICE_TYPE:
			self._valid = False

	def remove_activity(self, activity):
		actid = activity.get_id()
		if not self._activities.has_key(actid):
			return
		del self._activities[actid]
		print "Buddy (%s) left activity %s." % (self._nick_name, actid)
		self._dbus_helper.LeftActivity(activity.object_path())

	def get_service_of_type(self, stype=None, activity=None):
		"""Return a service of a certain type, or None if the buddy
		doesn't provide that service."""
		if not stype:
			raise RuntimeError("Need to specify a service type.")

		if activity:
			actid = activity.get_id()
			for service in self._services.values():
				if service.get_type() == stype and service.get_activity_id() == actid:
					return service
		if self._services.has_key(stype):
			return self._services[stype]
		return None

	def is_valid(self):
		"""Return whether the buddy is valid or not.  A buddy is
		not valid until its official presence service has been found
		and successfully resolved."""
		return self._valid

	def get_icon_pixbuf(self):
		if self._icon:
			pbl = gtk.gdk.PixbufLoader()
			pbl.write(self._icon)
			pbl.close()
			return pbl.get_pixbuf()
		else:
			return None

	def get_icon(self):
		"""Return the buddies icon, if any."""
		return self._icon
		
	def get_address(self):
		return self._address

	def get_nick_name(self):
		return self._nick_name

	def _set_icon(self, icon):
		"""Can only set icon for other buddies.  The Owner
		takes care of setting it's own icon."""
		if icon != self._icon:
			self._icon = icon
			self._dbus_helper.IconChanged()

	def is_owner(self):
		return self._owner


class Owner(Buddy):
	"""Class representing the owner of the machine.  This is the client
	portion of the Owner, paired with the server portion in Owner.py."""
	def __init__(self, bus_name, object_id, service):
		Buddy.__init__(self, bus_name, object_id, service, owner=True)
