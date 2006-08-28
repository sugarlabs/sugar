import gtk
import dbus

from sugar import conf
from sugar.activity import Activity
from sugar.presence import PresenceService
from sugar.canvas.IconColor import IconColor

class ActivityHost:
	def __init__(self, shell, window):
		self._shell = shell
		self._window = window
		self._xid = window.get_xid()

		bus = dbus.SessionBus()
		proxy_obj = bus.get_object(Activity.get_service_name(self._xid),
								   Activity.get_object_path(self._xid))

		self._activity = dbus.Interface(proxy_obj, Activity.ACTIVITY_INTERFACE)
		self._id = self._activity.get_id()
		self._default_type = self._activity.get_default_type()
		self._gdk_window = gtk.gdk.window_foreign_new(self._xid)

		registry = conf.get_activity_registry()
		info = registry.get_activity(self._default_type)
		self._icon_name = info.get_icon()

	def get_id(self):
		return self._id

	def get_icon_name(self):
		return self._icon_name

	def get_icon_color(self):
		pservice = PresenceService.get_instance()
		activity = pservice.get_activity(self._id)
		if activity != None:
			return IconColor(activity.get_color())
		else:
			return conf.get_profile().get_color()

	def share(self):
		self._activity.share()

	def get_shared(self):
		return self._activity.get_shared()

	def get_default_type(self):
		return self._default_type

	def present(self):
		self._window.activate(gtk.get_current_event_time())

	def show_dialog(self, dialog):
		dialog.show()
		dialog.window.set_transient_for(self._gdk_window)
