import gtk
import dbus

from sugar.activity import Activity
from PeopleWindow import PeopleWindow

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
		self._people_window = PeopleWindow(shell, self)

		info = self._shell.get_registry().get_activity(self._default_type)
		self._icon_name = info.get_icon()

	def get_id(self):
		return self._id

	def get_icon_name(self):
		return self._icon_name

	def share(self):
		self._people_window.share()
		self._activity.share()

	def get_shared(self):
		return self._activity.get_shared()

	def get_default_type(self):
		return self._default_type

	def show_people(self):
		self.show_dialog(self._people_window)

	def present(self):
		self._window.activate(gtk.get_current_event_time())

	def show_dialog(self, dialog):
		dialog.show()
		dialog.window.set_transient_for(self._gdk_window)
