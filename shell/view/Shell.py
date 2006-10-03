import gtk
import gobject
import wnck

from view.home.HomeWindow import HomeWindow
from sugar.presence import PresenceService
from view.ActivityHost import ActivityHost
from sugar.activity import ActivityFactory
from sugar.activity import Activity
from view.frame.Frame import Frame
from globalkeys import KeyGrabber
import sugar

class Shell(gobject.GObject):
	__gsignals__ = {
		'activity-opened':  (gobject.SIGNAL_RUN_FIRST,
							 gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT])),
		'activity-changed': (gobject.SIGNAL_RUN_FIRST,
							 gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT])),
		'activity-closed':  (gobject.SIGNAL_RUN_FIRST,
							 gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT]))
	}

	def __init__(self, model):
		gobject.GObject.__init__(self)

		self._model = model
		self._hosts = {}
		self._screen = wnck.screen_get_default()

		self._key_grabber = KeyGrabber()
		self._key_grabber.connect('key-pressed',
								  self.__global_key_pressed_cb)
		self._key_grabber.connect('key-released',
								  self.__global_key_released_cb)
		self._key_grabber.grab('F1')
		self._key_grabber.grab('F2')
		self._key_grabber.grab('F3')
		self._key_grabber.grab('F4')
		self._key_grabber.grab('F5')
		self._key_grabber.grab('F6')
		self._key_grabber.grab('F9')

		self._home_window = HomeWindow(self)
		self._home_window.show()
		self.set_zoom_level(sugar.ZOOM_HOME)

		self._screen.connect('window-opened', self.__window_opened_cb)
		self._screen.connect('window-closed', self.__window_closed_cb)
		self._screen.connect('active-window-changed',
							 self.__active_window_changed_cb)

		self._frame = Frame(self)
		self._frame.show_and_hide(3)

	def __global_key_pressed_cb(self, grabber, key):
		if key == 'F1':
			self.set_zoom_level(sugar.ZOOM_ACTIVITY)
		elif key == 'F2':
			self.set_zoom_level(sugar.ZOOM_HOME)
		elif key == 'F3':
			self.set_zoom_level(sugar.ZOOM_FRIENDS)
		elif key == 'F4':
			self.set_zoom_level(sugar.ZOOM_MESH)
		elif key == 'F5':
			self._frame.notify_key_press()
		elif key == 'F6':
			self.start_activity('org.sugar.Terminal')
		elif key == 'F9':
			self._show_hide_activity_chat()

	def __global_key_released_cb(self, grabber, key):
		if key == 'F5':
			self._frame.notify_key_release()

	def __window_opened_cb(self, screen, window):
		if window.get_window_type() == wnck.WINDOW_NORMAL:
			activity_host = ActivityHost(self, window)
			self._hosts[activity_host.get_xid()] = activity_host
			self.emit('activity-opened', activity_host)

	def __active_window_changed_cb(self, screen):
		window = screen.get_active_window()

		if window and window.get_window_type() == wnck.WINDOW_NORMAL:
			activity_host = self._hosts[window.get_xid()]

			current = self._model.get_current_activity()
			if activity_host.get_id() == current:
				return

			self._model.set_current_activity(activity_host.get_id())
			self.emit('activity-changed', activity_host)

	def __window_closed_cb(self, screen, window):
		if window.get_window_type() == wnck.WINDOW_NORMAL:
			if self._hosts.has_key(window.get_xid()):
				host = self._hosts[window.get_xid()]
				self.emit('activity-closed', host)
				del self._hosts[window.get_xid()]

		if len(self._hosts) == 0:
			self._model.set_current_activity(None)
			self.emit('activity-changed', None)

	def get_model(self):
		return self._model

	def join_activity(self, bundle_id, activity_id):
		pservice = PresenceService.get_instance()

		activity = self._get_activity(activity_id)
		if activity:
			activity.present()
		else:
			activity_ps = pservice.get_activity(activity_id)

			if activity_ps:
				activity = ActivityFactory.create(bundle_id)
				activity.join(activity_ps.object_path())
			else:
				logging.error('Cannot start activity.')

	def start_activity(self, activity_type):
		activity = ActivityFactory.create(activity_type)
		activity.execute('test', [])
		return activity

	def set_zoom_level(self, level):
		if level == sugar.ZOOM_ACTIVITY:
			self._screen.toggle_showing_desktop(False)
		else:
			self._screen.toggle_showing_desktop(True)
			self._home_window.set_zoom_level(level)

	def get_current_activity(self):
		activity_id = self._model.get_current_activity()
		if activity_id:
			return self._get_activity(activity_id)
		else:
			return None

	def _get_activity(self, activity_id):
		for host in self._hosts.values():
			if host.get_id() == activity_id:
				return host
		return None

	def _show_hide_activity_chat(self):
		act = self.get_current_activity()
		if not act:
			return
		is_visible = self._frame.is_visible()
		if act.is_chat_visible():
			frame_was_visible = act.chat_hide()
			if not frame_was_visible:
				self._frame.do_slide_out()
		else:
			if not is_visible:
				self._frame.do_slide_in()
			act.chat_show(is_visible)
