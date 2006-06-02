# -*- tab-width: 4; indent-tabs-mode: t -*- 

import dbus
import dbus.service
import dbus.glib
import pygtk
pygtk.require('2.0')
import gtk

SHELL_SERVICE_NAME = "com.redhat.Sugar.Shell"
SHELL_SERVICE_PATH = "/com/redhat/Sugar/Shell"

ACTIVITY_SERVICE_NAME = "com.redhat.Sugar.Activity"
ACTIVITY_SERVICE_PATH = "/com/redhat/Sugar/Activity"

class ActivityDbusService(dbus.service.Object):
	"""Base dbus service object that each Activity uses to export dbus methods.
	
	The dbus service is separate from the actual Activity object so that we can
	tightly control what stuff passes through the dbus python bindings."""

	def __init__(self, activity):
		self._activity = activity
		self._activity_id = None
		self._activity_object = None
		self._service = None
		self._bus = dbus.SessionBus()
		self._bus.add_signal_receiver(self.name_owner_changed, dbus_interface = "org.freedesktop.DBus", signal_name = "NameOwnerChanged")

	def __del__(self):
		if self._activity_id:
			del self._service
			del self._activity_container
			del self._activity_conainer_object
			del self._activity_object
		self._bus.remove_signal_receiver(self.name_owner_changed, dbus_interface="org.freedesktop.DBus", signal_name="NameOwnerChanged")
		del self._bus

	def connect_to_shell(self):
		"""Register with the shell via dbus, getting an activity ID and
		and XEMBED window ID in which to display the Activity."""
		self._activity_container_object = self._bus.get_object(SHELL_SERVICE_NAME, \
															   SHELL_SERVICE_PATH + "/ActivityContainer")
		self._activity_container = dbus.Interface(self._activity_container_object, \
												   SHELL_SERVICE_NAME + ".ActivityContainer")

		self._activity_id = self._activity_container.add_activity("")
		self._object_path = SHELL_SERVICE_PATH + "/Activities/%d" % self._activity_id

		print "ActivityDbusService: object path is '%s'" % self._object_path

		self._activity_object = dbus.Interface(self._bus.get_object(SHELL_SERVICE_NAME, self._object_path), \
											  SHELL_SERVICE_NAME + ".ActivityHost")

		# Now let us register a peer service so the Shell can poke it
		self._peer_service_name = ACTIVITY_SERVICE_NAME + "%d" % self._activity_id
		self._peer_object_path = ACTIVITY_SERVICE_PATH + "/%d" % self._activity_id
		self._service = dbus.service.BusName(self._peer_service_name, bus=self._bus)
		dbus.service.Object.__init__(self, self._service, self._peer_object_path)

		self._activity_object.set_peer_service_name(self._peer_service_name, self._peer_object_path)
		return (self._activity_object, self._activity_id)

	def _shutdown_reply_cb(self):
		"""Shutdown was successful, tell the Activity that we're disconnected."""
		self._activity.on_disconnected_from_shell()

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
			self._activity.on_disconnected_from_shell()
		elif service_name == SHELL_SERVICE_NAME and not len(old_service_name):
			self._activity.on_reconnected_to_shell()

	@dbus.service.method(ACTIVITY_SERVICE_NAME)
	def lost_focus(self):
		"""Called by the shell to notify us that we've lost focus."""
		self._activity.on_lost_focus()

	@dbus.service.method(ACTIVITY_SERVICE_NAME)
	def got_focus(self):
		"""Called by the shell to notify us that the user gave us focus."""
		self._activity.on_got_focus()

	@dbus.service.method(ACTIVITY_SERVICE_NAME)
	def close_from_user(self):
		"""Called by the shell to notify us that the user closed us."""
		self._activity.on_close_from_user()


class Activity(object):
	"""Base Activity class that all other Activities derive from."""

	def __init__(self):
		self._dbus_service = self._get_new_dbus_service()
		self._has_focus = False
		self._plug = None
		self._activity_object = None

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

	def has_focus(self):
		"""Return whether or not this Activity is visible to the user."""
		return self._has_focus

	def connect_to_shell(self):
		"""Called by our controller to tell us to initialize and connect
		to the shell."""
		(self._activity_object, self._activity_id) = self._dbus_service.connect_to_shell()
		self.on_connected_to_shell()

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
		if not self.get_has_focus() and has_changes:
			self._activity_object.set_has_changes(True)
		else:
			self._activity_object.set_has_changes(False)

	def activity_get_id(self):
		return self._activity_id

	def shutdown(self):
		"""Disconnect from the shell and clean up."""
		self._dbus_service.shutdown()

	def on_lost_focus(self):
		"""Triggered when this Activity loses focus."""
		self._has_focus = False;

	def on_got_focus(self):
		"""Triggered when this Activity gets focus."""
		self._has_focus = True
		self.set_has_changes(False)

	def on_disconnected_from_shell(self):
		"""Triggered when we disconnect from the shell."""
		self._cleanup()

	def on_reconnected_to_shell(self):
		"""Triggered when the shell's service comes back."""
		pass
 
	def on_connected_to_shell(self):
		"""Triggered when this Activity has successfully connected to the shell."""
		self._window_id = self._activity_object.get_host_xembed_id()
		print "Activity: XEMBED window ID is %d" % self._window_id
		self._plug = gtk.Plug(self._window_id)

	def on_close_from_user(self):
		"""Triggered when this Activity is closed by the user."""
		self.shutdown()
