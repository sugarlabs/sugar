import gtk
import dbus

from sugar.activity import Activity
from PeopleWindow import PeopleWindow

class ActivityHost:
	def __init__(self, shell, window):
		self._shell = shell

		xid = window.get_xid()

		bus = dbus.SessionBus()
		proxy_obj = bus.get_object(Activity.get_service_name(xid),
								   Activity.get_object_path(xid))

		self._activity = dbus.Interface(proxy_obj, Activity.ACTIVITY_INTERFACE)
		self._id = self._activity.get_id()
		self._default_type = self._activity.get_default_type()
		self._window = gtk.gdk.window_foreign_new(window.get_xid())
		self._people_window = PeopleWindow(shell, self)

	def get_id(self):
		return self._id

	def share(self):
		self._people_window.share()
		self._activity.share()

	def get_shared(self):
		return self._activity.get_shared()

	def get_default_type(self):
		return self._default_type

	def show_people(self):
		self.show_dialog(self._people_window)

	def show_dialog(self, dialog):
		dialog.show()
		dialog.window.set_transient_for(self._window)
