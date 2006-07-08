import dbus
import gtk
import gobject

from sugar.chat.ActivityChat import ActivityChat
from WindowManager import WindowManager
import sugar.util

class ActivityHostSignalHelper(gobject.GObject):
	__gsignals__ = {
		'shared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([]))
	}

	def __init__(self, parent):
		gobject.GObject.__init__(self)
		self._parent = parent

	def emit_shared(self):
		self.emit('shared')

class ActivityHost(dbus.service.Object):
	def __init__(self, bus_name, default_type, activity_id = None):
		if activity_id is None:
			self._activity_id = sugar.util.unique_id()
		else:
			self._activity_id = activity_id
		self._default_type = default_type	
	
		self.dbus_object_name = "/com/redhat/Sugar/Shell/Activities/%s" % self._activity_id
		dbus.service.Object.__init__(self, bus_name, self.dbus_object_name)

		self._signal_helper = ActivityHostSignalHelper(self)
		self.peer_service = None
		self._shared = False

		self._create_chat()

	def _create_chat(self):
		self._activity_chat = ActivityChat(self)

	def got_focus(self):
		if self.peer_service != None:
			self.peer_service.got_focus()
	
	def lost_focus(self):
		self.peer_service.lost_focus()

	def get_chat(self):
		return self._activity_chat

	def get_default_type(self):
		return self._default_type

	def publish(self):
		self._activity_chat.publish()
		self.peer_service.publish()
	
	def connect(self, signal, func):
		self._signal_helper.connect(signal, func)
		
	def get_id(self):
		"""Interface-type function to match activity.Activity's
		get_id() function."""
		return self._activity_id

	def default_type(self):
		"""Interface-type function to match activity.Activity's
		default_type() function."""
		return self._default_type

	def get_object_path(self):
		return self.dbus_object_name
		
	def get_shared(self):
		"""Return True if this activity is shared, False if
		it has not been shared yet."""
		return self._shared

	def _shared_signal(self):
		self._shared = True
		self._signal_helper.emit_shared()

	@dbus.service.method("com.redhat.Sugar.Shell.ActivityHost")
	def set_peer_service_name(self, peer_service_name, peer_object_name):
		self.__peer_service_name = peer_service_name
		self.__peer_object_name = peer_object_name
		session_bus = dbus.SessionBus()
		self.peer_service = dbus.Interface(session_bus.get_object( \
				self.__peer_service_name, self.__peer_object_name), \
										   "com.redhat.Sugar.Activity")
		session_bus.add_signal_receiver(self._shared_signal,
				signal_name="ActivityShared",
				dbus_interface="com.redhat.Sugar.Activity",
				named_service=self.__peer_service_name,
				path=self.__peer_object_name)

	@dbus.service.method("com.redhat.Sugar.Shell.ActivityHost")
	def set_has_changes(self, has_changes):
		pass
		
	@dbus.service.method("com.redhat.Sugar.Shell.ActivityHost")
	def set_title(self, text):
		pass

	@dbus.service.method("com.redhat.Sugar.Shell.ActivityHost")
	def set_icon(self, data, colorspace, has_alpha, bits_per_sample, width, height, rowstride):
		pixstr = ""
		for c in data:
			# Work around for a bug in dbus < 0.61 where integers
			# are not correctly marshalled
			if c < 0:
				c += 256
			pixstr += chr(c)

		pixbuf = gtk.gdk.pixbuf_new_from_data(pixstr, colorspace, has_alpha,
											  bits_per_sample, width, height, rowstride)

	@dbus.service.method("com.redhat.Sugar.Shell.ActivityHost")
	def shutdown(self):
		for owner, activity in self.activity_container.activities[:]:
			if activity == self:
				self.activity_container.activities.remove((owner, activity))
				
		for i in range(self.activity_container.notebook.get_n_pages()):
			child = self.activity_container.notebook.get_nth_page(i)
			if child == self.socket:
				self.activity_container.notebook.remove_page(i)
				break

		del self
