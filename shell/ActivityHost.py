import gtk
import dbus

from sugar.activity import Activity

class ActivityHost:
	def __init__(self, xid):
		self._xid = xid
		
		bus = dbus.SessionBus()
		service = Activity.ACTIVITY_SERVICE_NAME + "%s" % xid
		path = Activity.ACTIVITY_SERVICE_PATH + "/%s" % xid
		proxy_obj = bus.get_object(service, path)

		self._activity = dbus.Interface(proxy_obj, 'com.redhat.Sugar.Activity')
		self._id = self._activity.get_id()
		self._default_type = self._activity.get_default_type()
		self._window = gtk.gdk.window_foreign_new(xid)

	def get_id(self):
		return self._id

	def publish(self):
		self._activity.publish()

	def get_shared(self):
		return self._activity.get_shared()

	def get_default_type(self):
		return self._default_type

	def show_dialog(self, dialog):
		dialog.show()
		dialog.window.set_transient_for(self._window)
