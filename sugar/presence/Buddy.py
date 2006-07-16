import base64
import logging

import gtk
import gobject

from sugar.p2p import Stream
from sugar.p2p import network
from sugar.presence import Service

PRESENCE_SERVICE_TYPE = "_presence_olpc._tcp"

class Buddy(gobject.GObject):
	"""Represents another person on the network and keeps track of the
	activities and resources they make available for sharing."""
	__gsignals__ = {
		'icon-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([])),
		'service-added': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([gobject.TYPE_PYOBJECT])),
		'service-removed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([gobject.TYPE_PYOBJECT])),
		'joined-activity': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([gobject.TYPE_STRING])),
		'left-activity': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([gobject.TYPE_STRING]))
	}

	def __init__(self, service):
		gobject.GObject.__init__(self)
		self._services = {}
		self._nick_name = service.get_name()
		self._address = service.get_publisher_address()
		self._valid = False
		self._icon = None
		self._icon_tries = 0
		self._owner = False
		self.add_service(service)

	def _request_buddy_icon_cb(self, result_status, response, user_data):
		"""Callback when icon request has completed."""
		icon = response
		service = user_data
		if result_status == network.RESULT_SUCCESS:
			if icon and len(icon):
				icon = base64.b64decode(icon)
				print "Buddy icon for '%s' is size %d" % (self._nick_name, len(icon))
				self.set_icon(icon)

		if (result_status == network.RESULT_FAILED or not icon) and self._icon_tries < 3:
			self._icon_tries = self._icon_tries + 1
			print "Failed to retrieve buddy icon for '%s' on try %d of %d" % (self._nick_name, \
					self._icon_tries, 3)
			gobject.timeout_add(1000, self._request_buddy_icon, service)
		return False

	def _request_buddy_icon(self, service):
		"""Contact the buddy to retrieve the buddy icon."""
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
		if self._valid:
			self.emit("service-added", service)

		# If this is the first service we've seen that's owned  by
		# a particular activity, send out the 'joined-activity' signal
		actid = service.get_activity_id()
		if actid is not None:
			found = False
			for serv in self._services.values():
				if serv.get_activity_id() == actid and serv.get_type() != stype:
					found = True
					break
			if not found:
				print "Buddy (%s) joined activity %s." % (self._nick_name, actid)
				self.emit("joined-activity", service)

		if stype == PRESENCE_SERVICE_TYPE:
			# A buddy isn't valid until its official presence
			# service has been found and resolved
			self._valid = True
			print 'Requesting buddy icon %s' % self._nick_name
			self._request_buddy_icon(service)
		return True

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
				self.emit("service-removed", service)
			del self._services[stype]

		# If this is the lase service owned  by a particular activity,
		# and it's just been removed, send out the 'left-actvity' signal
		actid = service.get_activity_id()
		if actid is not None:
			found = False
			for serv in self._services.values():
				if serv.get_activity_id() == actid:
					found = True
					break
			if not found:
				print "Buddy (%s) left activity %s." % (self._nick_name, actid)
				self.emit("left-activity", service)

		if stype == PRESENCE_SERVICE_TYPE:
			self._valid = False

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

	def set_icon(self, icon):
		"""Can only set icon for other buddies.  The Owner
		takes care of setting it's own icon."""
		if icon != self._icon:
			self._icon = icon
			self.emit("icon-changed")

	def is_owner(self):
		return self._owner


class Owner(Buddy):
	"""Class representing the owner of the machine.  This is the client
	portion of the Owner, paired with the server portion in Owner.py."""
	def __init__(self, service):
		Buddy.__init__(self, service)
		self._owner = True
