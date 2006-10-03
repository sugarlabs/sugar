import gtk
import dbus

import conf
from sugar.activity import Activity
from sugar.presence import PresenceService
from sugar.graphics.iconcolor import IconColor
from sugar.p2p import Stream
from sugar.p2p import network
from sugar.chat import ActivityChat
import OverlayWindow

class ActivityChatWindow(gtk.Window):
	def __init__(self, gdk_window, chat_widget):
		gtk.Window.__init__(self)

		self.realize()
		self.set_decorated(False)
		self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
		self.window.set_accept_focus(True)		
		self.window.set_transient_for(gdk_window)
		self.set_position(gtk.WIN_POS_CENTER_ALWAYS)
		self.set_default_size(600, 450)

		self.add(chat_widget)

class ActivityHost:
	def __init__(self, shell, window):
		self._shell = shell

		self._window = window
		self._xid = window.get_xid()
		self._pservice = PresenceService.get_instance()

		bus = dbus.SessionBus()
		proxy_obj = bus.get_object(Activity.get_service_name(self._xid),
								   Activity.get_object_path(self._xid))

		self._activity = dbus.Interface(proxy_obj, Activity.ACTIVITY_INTERFACE)
		self._id = self._activity.get_id()
		self._type = self._activity.get_type()
		self._gdk_window = gtk.gdk.window_foreign_new(self._xid)

		registry = conf.get_activity_registry()
		info = registry.get_activity(self._type)
		self._icon_name = info.get_icon()

		try:
			self._overlay_window = OverlayWindow.OverlayWindow(self._gdk_window)
			win = self._overlay_window.window
		except RuntimeError:
			self._overlay_window = None
			win = self._gdk_window

		self._chat_widget = ActivityChat.ActivityChat(self)
		self._chat_window = ActivityChatWindow(win, self._chat_widget)

		self._frame_was_visible = False
		self._shell.connect('activity-changed', self._activity_changed_cb)
		self._shell.connect('activity-closed', self._activity_closed_cb)

	def get_id(self):
		return self._id

	def get_title(self):
		return self._window.get_name()

	def get_xid(self):
		return self._xid

	def get_icon_name(self):
		return self._icon_name

	def get_icon_color(self):
		activity = self._pservice.get_activity(self._id)
		if activity != None:
			return IconColor(activity.get_color())
		else:
			return conf.get_profile().get_color()

	def share(self):
		self._activity.share()
		self._chat_widget.share()

	def invite(self, buddy):
		if not self.get_shared():
			self.share()

		issuer = self._pservice.get_owner().get_name()
		service = buddy.get_service_of_type("_presence_olpc._tcp")
		stream = Stream.Stream.new_from_service(service, start_reader=False)
		writer = stream.new_writer(service)
		writer.custom_request("invite", None, None, issuer,
							  self._type, self._id)

	def get_shared(self):
		return self._activity.get_shared()

	def get_type(self):
		return self._type

	def present(self):
		self._window.activate(gtk.get_current_event_time())

	def close(self):
		self._window.close(gtk.get_current_event_time())

	def show_dialog(self, dialog):
		dialog.show()
		dialog.window.set_transient_for(self._gdk_window)

	def chat_show(self, frame_was_visible):
		if self._overlay_window:
			self._overlay_window.show_all()
		self._chat_window.show_all()
		self._frame_was_visible = frame_was_visible

	def chat_hide(self):
		self._chat_window.hide()
		if self._overlay_window:
			self._overlay_window.hide()
		wasvis = self._frame_was_visible
		self._frame_was_visible = False
		return wasvis

	def is_chat_visible(self):
		return self._chat_window.get_property('visible')

	def _activity_changed_cb(self, shell, activity):
		if activity != self:
			self.chat_hide()
			self._frame_was_visible = False

	def _activity_closed_cb(self, shell, activity):
		if activity == self:
			self.chat_hide()
			self._frame_was_visible = False

