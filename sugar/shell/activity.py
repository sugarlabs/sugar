# -*- tab-width: 4; indent-tabs-mode: t -*- 

import dbus
import dbus.service
import dbus.glib
import pygtk
pygtk.require('2.0')
import gtk, gobject

SHELL_SERVICE_NAME = "com.redhat.Sugar.Shell"
SHELL_SERVICE_PATH = "/com/redhat/Sugar/Shell"

ACTIVITY_SERVICE_NAME = "com.redhat.Sugar.Activity"
ACTIVITY_SERVICE_PATH = "/com/redhat/Sugar/Activity"

ON_CONNECTED_TO_SHELL_CB = "connected_to_shell"
ON_DISCONNECTED_FROM_SHELL_CB = "disconnected_from_shell"
ON_RECONNECTED_TO_SHELL_CB = "reconnected_to_shell"
ON_CLOSE_FROM_USER_CB = "close_from_user"
ON_LOST_FOCUS_CB = "lost_focus"
ON_GOT_FOCUS_CB = "got_focus"
ON_PUBLISH_CB = "publish"

class ActivityDbusService(dbus.service.Object):
	"""Base dbus service object that each Activity uses to export dbus methods.
	
	The dbus service is separate from the actual Activity object so that we can
	tightly control what stuff passes through the dbus python bindings."""

	_ALLOWED_CALLBACKS = [ON_CONNECTED_TO_SHELL_CB, ON_DISCONNECTED_FROM_SHELL_CB, \
			ON_RECONNECTED_TO_SHELL_CB, ON_CLOSE_FROM_USER_CB, ON_LOST_FOCUS_CB, \
			ON_GOT_FOCUS_CB, ON_PUBLISH_CB]

	def __init__(self, activity):
		self._activity = activity
		self._activity_id = None
		self._activity_object = None
		self._service = None
		self._bus = dbus.SessionBus()
		self._bus.add_signal_receiver(self.name_owner_changed, dbus_interface = "org.freedesktop.DBus", signal_name = "NameOwnerChanged")
		self._callbacks = {}
		for cb in self._ALLOWED_CALLBACKS:
			self._callbacks[cb] = None

	def __del__(self):
		if self._activity_id:
			del self._service
			del self._activity_container
			del self._activity_conainer_object
			del self._activity_object
		self._bus.remove_signal_receiver(self.name_owner_changed, dbus_interface="org.freedesktop.DBus", signal_name="NameOwnerChanged")
		del self._bus

	def register_callback(self, name, callback):
		if name not in self._ALLOWED_CALLBACKS:
			print "ActivityDbusService: bad callback registration request for '%s'" % name
			return
		self._callbacks[name] = callback

	def _call_callback_cb(self, func, *args):
		gobject.idle_add(func, *args)
		return False

	def _call_callback(self, name, *args):
		"""Call our activity object back, but from an idle handler
		to minimize the possibility of stupid activities deadlocking
		in dbus callbacks."""
		if name in self._ALLOWED_CALLBACKS and self._callbacks[name]:
			gobject.idle_add(self._call_callback_cb, self._callbacks[name], *args)

	def connect_to_shell(self, service=None):
		"""Register with the shell via dbus, getting an activity ID and
		and XEMBED window ID in which to display the Activity."""
		self._activity_container_object = self._bus.get_object(SHELL_SERVICE_NAME, \
															   SHELL_SERVICE_PATH + "/ActivityContainer")
		self._activity_container = dbus.Interface(self._activity_container_object, \
												   SHELL_SERVICE_NAME + ".ActivityContainer")

		if service is None:
			self._activity_id = self._activity_container.add_activity("", self._activity.default_type())
		else:
			self._activity_id = serivce.get_activity_uid()
			self._activity_container.add_activity_with_id("", self._activity.default_type(), activity_id)
			
		self._object_path = SHELL_SERVICE_PATH + "/Activities/%s" % self._activity_id

		print "ActivityDbusService: object path is '%s'" % self._object_path

		self._activity_object = dbus.Interface(self._bus.get_object(SHELL_SERVICE_NAME, self._object_path), \
											  SHELL_SERVICE_NAME + ".ActivityHost")

		# Now let us register a peer service so the Shell can poke it
		self._peer_service_name = ACTIVITY_SERVICE_NAME + "%s" % self._activity_id
		self._peer_object_path = ACTIVITY_SERVICE_PATH + "/%s" % self._activity_id
		self._service = dbus.service.BusName(self._peer_service_name, bus=self._bus)
		dbus.service.Object.__init__(self, self._service, self._peer_object_path)

		self._activity_object.set_peer_service_name(self._peer_service_name, self._peer_object_path)

		self._call_callback(ON_CONNECTED_TO_SHELL_CB, self._activity_object, self._activity_id, service)

	def _shutdown_reply_cb(self):
		"""Shutdown was successful, tell the Activity that we're disconnected."""
		self._call_callback(ON_DISCONNECTED_FROM_SHELL_CB)

	def _shutdown_error_cb(self, error):
		print "ActivityDbusService: error during shutdown - '%s'" % error

	def shutdown(self):
		"""Notify the shell that we are shutting down."""
		self._activity_object.shutdown(reply_handler=self._shutdown_reply_cb, error_handler=self._shutdown_error_cb)

	def name_owner_changed(self, service_name, old_service_name, new_service_name):
		"""Handle dbus NameOwnerChanged signals."""
		if not self._activity_id:
			# Do nothing if we're not connected yet
			return

		if service_name == SHELL_SERVICE_NAME and not len(new_service_name):
			self._call_callback(ON_DISCONNECTED_FROM_SHELL_CB)
		elif service_name == SHELL_SERVICE_NAME and not len(old_service_name):
			self._call_callback(ON_RECONNECTED_TO_SHELL_CB)

	@dbus.service.method(ACTIVITY_SERVICE_NAME)
	def lost_focus(self):
		"""Called by the shell to notify us that we've lost focus."""
		self._call_callback(ON_LOST_FOCUS_CB)

	@dbus.service.method(ACTIVITY_SERVICE_NAME)
	def got_focus(self):
		"""Called by the shell to notify us that the user gave us focus."""
		self._call_callback(ON_GOT_FOCUS_CB)

	@dbus.service.method(ACTIVITY_SERVICE_NAME)
	def close_from_user(self):
		"""Called by the shell to notify us that the user closed us."""
		self._call_callback(ON_CLOSE_FROM_USER_CB)

	@dbus.service.method(ACTIVITY_SERVICE_NAME)
	def publish(self):
		"""Called by the shell to request the activity to publish itself on the network."""
		self._call_callback(ON_PUBLISH_CB)

class Activity(object):
	"""Base Activity class that all other Activities derive from."""

	def __init__(self, default_type):
		self._dbus_service = self._get_new_dbus_service()
		self._dbus_service.register_callback(ON_CONNECTED_TO_SHELL_CB, self._internal_on_connected_to_shell_cb)
		self._dbus_service.register_callback(ON_DISCONNECTED_FROM_SHELL_CB, self._internal_on_disconnected_from_shell_cb)
		self._dbus_service.register_callback(ON_RECONNECTED_TO_SHELL_CB, self._internal_on_reconnected_to_shell_cb)
		self._dbus_service.register_callback(ON_CLOSE_FROM_USER_CB, self._internal_on_close_from_user_cb)
		self._dbus_service.register_callback(ON_PUBLISH_CB, self._internal_on_publish_cb)
		self._dbus_service.register_callback(ON_LOST_FOCUS_CB, self._internal_on_lost_focus_cb)
		self._dbus_service.register_callback(ON_GOT_FOCUS_CB, self._internal_on_got_focus_cb)
		self._has_focus = False
		self._plug = None
		self._initial_service = None
		self._activity_object = None
		if type(default_type) != type("") or not len(default_type):
			raise ValueError("Default type must be a valid string.")
		self._default_type = default_type

	def _cleanup(self):
		if self._plug:
			self._plug.destroy()
			self._plug = None
		if self._dbus_service:
			del self._dbus_service
			self._dbus_service = None

	def __del__(self):
		self._cleanup()

	def _get_new_dbus_service(self):
		"""Create and return a new dbus service object for this Activity.
		Allows subclasses to use their own dbus service object if they choose."""
		return ActivityDbusService(self)

	def default_type(self):
		return self._default_type

	def has_focus(self):
		"""Return whether or not this Activity is visible to the user."""
		return self._has_focus

	def connect_to_shell(self, service = None):
		"""Called by our controller to tell us to initialize and connect
		to the shell."""
		self._dbus_service.connect_to_shell(service)

	def _internal_on_connected_to_shell_cb(self, activity_object, activity_id, service=None):
		"""Callback when the dbus service object has connected to the shell."""
		self._activity_object = activity_object
		self._activity_id = activity_id
		self._window_id = self._activity_object.get_host_xembed_id()
		print "Activity: XEMBED window ID is %s" % self._window_id
		self._plug = gtk.Plug(self._window_id)
		self._initial_service = service
		self.on_connected_to_shell()

	def _internal_on_disconnected_from_shell_cb(self):
		"""Callback when the dbus service object has disconnected from the shell."""
		self._cleanup()
		self.on_disconnected_from_shell()

	def _internal_on_reconnected_to_shell_cb(self):
		"""Callback when the dbus service object has reconnected to the shell."""
		self.on_reconnected_to_shell()

	def _internal_on_close_from_user_cb(self):
		"""Callback when the dbus service object tells us the user has closed our activity."""
		self.shutdown()
		self.on_close_from_user()

	def _internal_on_publish_cb(self):
		"""Callback when the dbus service object tells us the user has closed our activity."""
		self.publish()

	def _internal_on_lost_focus_cb(self):
		"""Callback when the dbus service object tells us we have lost focus."""
		self._has_focus = False
		self.on_lost_focus()

	def _internal_on_got_focus_cb(self):
		"""Callback when the dbus service object tells us we have gotten focus."""
		self._has_focus = True
		self.set_has_changes(False)
		self.on_got_focus()

	def gtk_plug(self):
		"""Return our GtkPlug widget."""
		return self._plug

	def set_ellipsize_tab(self, ellipsize):
		"""Sets this Activity's tab text to be ellipsized or not."""
		self._activity_object.set_ellipsize_tab(ellipsize)

	def set_tab_text(self, text):
		"""Sets this Activity's tab text."""
		self._activity_object.set_tab_text(text)

	def set_can_close(self, can_close):
		"""Sets whether or not this Activity can be closed by the user."""
		self._activity_object.set_can_close(can_close)

	def set_show_tab_icon(self, show_icon):
		"""Sets whether or not an icon is shown in this Activity's tab."""
		self._activity_object.set_tab_show_icon(show_icon)

	def set_tab_icon(self, pixbuf=None, name=None):
		"""Set the Activity's tab icon, either from pixbuf data
		or by an icon theme icon name."""
		if name:
			icon_theme = gtk.icon_theme_get_default()
			icon_info = icon_theme.lookup_icon(name, gtk.ICON_SIZE_MENU, 0)
			if icon_info:
				orig_pixbuf = icon_info.load_icon()
				pixbuf = orig_pixbuf.scale_simple(16, 16, gtk.gdk.INTERP_BILINEAR)

		if pixbuf:
			# Dump the pixel data into an array and shove it through dbus
			pixarray = []
			pixstr = pixbuf.get_pixels();
			for c in pixstr:
				pixarray.append(c)
			self._activity_object.set_tab_icon(pixarray, \
												pixbuf.get_colorspace(), \
												pixbuf.get_has_alpha(),  \
												pixbuf.get_bits_per_sample(), \
												pixbuf.get_width(), \
												pixbuf.get_height(), \
												pixbuf.get_rowstride())

	def set_has_changes(self, has_changes):
		"""Marks this Activity as having changes.  This usually means
		that this Activity's tab turns a red color or something else
		to notify the user that this Activity needs attention."""
		if not self.has_focus() and has_changes:
			self._activity_object.set_has_changes(True)
		else:
			self._activity_object.set_has_changes(False)

	def get_id(self):
		return self._activity_id

	def shutdown(self):
		"""Disconnect from the shell and clean up."""
		self._dbus_service.shutdown()

	#############################################################
	# Pure Virtual methods that subclasses may/may not implement
	#############################################################

	def publish(self):
		"""Called to request the activity to publish itself on the network."""
		pass

	def on_lost_focus(self):
		"""Triggered when this Activity loses focus."""
		pass

	def on_got_focus(self):
		"""Triggered when this Activity gets focus."""
		pass

	def on_disconnected_from_shell(self):
		"""Triggered when we disconnect from the shell."""
		pass

	def on_reconnected_to_shell(self):
		"""Triggered when the shell's service comes back."""
		pass
 
	def on_connected_to_shell(self):
		"""Triggered when this Activity has successfully connected to the shell."""
		pass

	def on_close_from_user(self):
		"""Triggered when this Activity is closed by the user."""
		pass
