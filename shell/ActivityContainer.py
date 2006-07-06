import dbus
import gobject
import gtk
from gettext import gettext as _

from sugar.chat.ChatWindow import ChatWindow
from sugar.chat.MeshChat import MeshChat
from ActivityHost import ActivityHost
from PresenceWindow import PresenceWindow
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
		self.activities = []

		self.bus = bus
		self.service = service

		self._signal_helper = ActivityContainerSignalHelper(self)

		dbus.service.Object.__init__(self, self.service, "/com/redhat/Sugar/Shell/ActivityContainer")
		bus.add_signal_receiver(self.name_owner_changed, dbus_interface = "org.freedesktop.DBus", signal_name = "NameOwnerChanged")

		self.window = gtk.Window()
		self.window.connect("key-press-event", self.__key_press_event_cb)
		self.window.set_title("OLPC Sugar")

		self._fullscreen = False

		self.notebook = gtk.Notebook()
		self.notebook.set_scrollable(True)

		tab_label = gtk.Label(_("Everyone"))
		self._start_page = StartPage(self._signal_helper)
		self.notebook.append_page(self._start_page, tab_label)
		self._start_page.show()

		self.notebook.show()
		self.notebook.connect("switch-page", self.notebook_tab_changed)
		self.window.add(self.notebook)
		
		self.window.connect("destroy", lambda w: gtk.main_quit())
		
		self.current_activity = None

		# Create our owner service
		self._owner = ShellOwner()

		self._presence_window = PresenceWindow(self)
		self._presence_window.set_transient_for(self.window)
		self._presence_window.set_decorated(False)
		self._presence_window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DOCK)
		self._presence_window.set_skip_taskbar_hint(True)

		wm = WindowManager(self._presence_window)
	
		wm.set_width(170, WindowManager.ABSOLUTE)
		wm.set_height(1.0, WindowManager.SCREEN_RELATIVE)
		wm.set_position(WindowManager.LEFT)
		wm.manage()
		
		self._chat_window = ChatWindow()
		self._chat_window.set_transient_for(self.window)
		self._chat_window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DOCK)
		self._chat_window.set_decorated(False)
		self._chat_window.set_skip_taskbar_hint(True)

		self._chat_wm = WindowManager(self._chat_window)
		
		self._chat_wm.set_width(420, WindowManager.ABSOLUTE)
		self._chat_wm.set_height(380, WindowManager.ABSOLUTE)
		self._chat_wm.set_position(WindowManager.TOP)
		self._chat_wm.manage()
		
		self._mesh_chat = MeshChat()

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

		# For some reason the substitution screw up window position
		self._chat_wm.update()

	def notebook_tab_changed(self, notebook, page, page_number):
		new_activity = notebook.get_nth_page(page_number).get_data("sugar-activity")

		if self.current_activity != None:
			self.current_activity.lost_focus()
		
		self.set_current_activity(new_activity)

		if self.current_activity != None:
			self.current_activity.got_focus()

	def name_owner_changed(self, service_name, old_service_name, new_service_name):
		#print "in name_owner_changed: svc=%s oldsvc=%s newsvc=%s"%(service_name, old_service_name, new_service_name)
		for owner, activity in self.activities[:]:
			if owner == old_service_name:
				activity_id = activity.get_host_activity_id()
				self._signal_helper.activity_ended(activity_id)
				self.activities.remove((owner, activity))
		#self.__print_activities()


	@dbus.service.method("com.redhat.Sugar.Shell.ActivityContainer", \
			 in_signature="ss", \
			 out_signature="s", \
			 sender_keyword="sender")
	def add_activity(self, activity_name, default_type, sender):
		#print "hello world, activity_name = '%s', sender = '%s'"%(activity_name, sender)
		activity = ActivityHost(self, activity_name, default_type)
		self.activities.append((sender, activity))

		activity_id = activity.get_host_activity_id()
		self._signal_helper.activity_started(activity_id)

		self.current_activity = activity
		return activity_id

	@dbus.service.method("com.redhat.Sugar.Shell.ActivityContainer", \
			 in_signature="sss", \
			 sender_keyword="sender")
	def add_activity_with_id(self, activity_name, default_type, activity_id, sender):
		activity = ActivityHost(self, activity_name, default_type, activity_id)
		self.activities.append((sender, activity))
		activity_id = activity.get_host_activity_id()
		self._signal_helper.activity_started(activity_id)
		self.current_activity = activity
		
	def __print_activities(self):
		print "__print_activities: %d activities registered" % len(self.activities)
		i = 0
		for owner, activity in self.activities:
			print "  %d: owner=%s activity_object_name=%s" % (i, owner, activity.dbus_object_name)
			i += 1
	
	def __key_press_event_cb(self, window, event):
		if event.keyval == gtk.keysyms.F11:
			if self._fullscreen:
				window.unfullscreen()
				self._fullscreen = False
			else:
				window.fullscreen()
				self._fullscreen = True			

