import dbus
import gobject
import gtk
from gettext import gettext as _

from sugar.chat.ChatWindow import ChatWindow
from sugar.chat.MeshChat import MeshChat
from ActivityHost import ActivityHost
from PresenceWindow import PresenceWindow
from HomeWindow import HomeWindow
from WindowManager import WindowManager
from StartPage import StartPage
from Owner import ShellOwner

class ActivityContainerSignalHelper(gobject.GObject):
	"""A gobject whose sole purpose is to distribute signals for
	an ActivityContainer object."""

	__gsignals__ = {
		'local-activity-started': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT])),
		'local-activity-ended': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT]))
	}

	def __init__(self, parent):
		gobject.GObject.__init__(self)
		self._parent = parent

	def activity_started(self, activity_id):
		self.emit('local-activity-started', self._parent, activity_id)

	def activity_ended(self, activity_id):
		self.emit('local-activity-ended', self._parent, activity_id)

class ActivityContainer(dbus.service.Object):
	def __init__(self, service, bus):
		self._activities = []
		self._bus = bus
		self._service = service
		self._signal_helper = ActivityContainerSignalHelper(self)
		self._current_activity = None

		dbus.service.Object.__init__(self, self._service,
									 "/com/redhat/Sugar/Shell/ActivityContainer")
		bus.add_signal_receiver(self.name_owner_changed,
								dbus_interface = "org.freedesktop.DBus",
								signal_name = "NameOwnerChanged")

		# Create our owner service
		self._owner = ShellOwner()

		self._presence_window = PresenceWindow(self)
		wm = WindowManager(self._presence_window)
		wm.set_type(WindowManager.TYPE_POPUP)
		wm.set_animation(WindowManager.ANIMATION_SLIDE_IN)
		wm.set_geometry(0.02, 0.1, 0.25, 0.9)
		wm.set_key(gtk.keysyms.F1)
		
		self._chat_window = ChatWindow()
		chat_wm = WindowManager(self._chat_window)
		chat_wm.set_animation(WindowManager.ANIMATION_SLIDE_IN)
		chat_wm.set_type(WindowManager.TYPE_POPUP)
		chat_wm.set_geometry(0.28, 0.1, 0.5, 0.9)
		chat_wm.set_key(gtk.keysyms.F1)
				
		self._mesh_chat = MeshChat()

		home_window = HomeWindow()
		wm = WindowManager(home_window)
		wm.set_type(WindowManager.TYPE_POPUP)
		wm.set_animation(WindowManager.ANIMATION_SLIDE_IN)
		wm.set_geometry(0.1, 0.1, 0.9, 0.9)
		wm.set_key(gtk.keysyms.F2)

	def show(self):
		self.window.show()

	def set_current_activity(self, activity):
		self.current_activity = activity
		self._presence_window.set_activity(activity)

		if activity:
			host_chat = activity.get_chat()
			self._chat_window.set_chat(host_chat)
		else:
			self._chat_window.set_chat(self._mesh_chat)

	def name_owner_changed(self, service_name, old_service_name, new_service_name):
		for owner, activity in self._activities[:]:
			if owner == old_service_name:
				activity_id = activity.get_host_activity_id()
				self._signal_helper.activity_ended(activity_id)
				self._activities.remove((owner, activity))

	@dbus.service.method("com.redhat.Sugar.Shell.ActivityContainer", \
			 in_signature="ss", \
			 out_signature="s", \
			 sender_keyword="sender")
	def add_activity(self, activity_name, default_type, sender):
		activity = ActivityHost(self, activity_name, default_type)
		self._activities.append((sender, activity))

		activity_id = activity.get_host_activity_id()
		self._signal_helper.activity_started(activity_id)

		self.current_activity = activity
		return activity_id

	@dbus.service.method("com.redhat.Sugar.Shell.ActivityContainer", \
			 in_signature="sss", \
			 sender_keyword="sender")
	def add_activity_with_id(self, activity_name, default_type, activity_id, sender):
		activity = ActivityHost(self, activity_name, default_type, activity_id)
		self._activities.append((sender, activity))
		activity_id = activity.get_host_activity_id()
		self._signal_helper.activity_started(activity_id)
		self.current_activity = activity
