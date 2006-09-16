import gtk
import gobject
import wnck

from sugar.canvas.Grid import Grid
from view.home.HomeWindow import HomeWindow
from sugar.presence import PresenceService
from view.ActivityHost import ActivityHost
from sugar.activity import ActivityFactory
from sugar.activity import Activity
from view.frame.Frame import Frame
from globalkeys import KeyGrabber
import sugar

class Shell(gobject.GObject):
	def __init__(self, model):
		gobject.GObject.__init__(self)

		self._model = model
		self._screen = wnck.screen_get_default()
		self._grid = Grid()

		self._key_grabber = KeyGrabber()
		self._key_grabber.connect('key-pressed', self.__global_key_pressed_cb)
		self._key_grabber.grab('F1')
		self._key_grabber.grab('F2')
		self._key_grabber.grab('F3')
		self._key_grabber.grab('F4')
		self._key_grabber.grab('F5')
		self._key_grabber.grab('F6')

		self._home_window = HomeWindow(self)
		self._home_window.show()
		self.set_zoom_level(sugar.ZOOM_HOME)

		self._screen.connect('window-opened', self.__window_opened_cb)
		self._screen.connect('window-closed', self.__window_closed_cb)
		self._screen.connect('active-window-changed',
							 self.__active_window_changed_cb)

		self._frame = Frame(self)
		self._frame.show_and_hide(10)

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
			self._frame.toggle_visibility()
		elif key == 'F6':
			self.start_activity('org.sugar.Terminal')

	def __window_opened_cb(self, screen, window):
		if window.get_window_type() == wnck.WINDOW_NORMAL:
			self._model.add_activity(ActivityHost(self, window))

	def __active_window_changed_cb(self, screen):
		window = screen.get_active_window()
		if window and window.get_window_type() == wnck.WINDOW_NORMAL:
			self._model.set_current_activity(window.get_xid())

	def __window_closed_cb(self, screen, window):
		if window.get_window_type() == wnck.WINDOW_NORMAL:
			self._model.remove_activity(window.get_xid())

	def get_model(self):
		return self._model

	def get_grid(self):
		return self._grid

	def join_activity(self, bundle_id, activity_id):
		pservice = PresenceService.get_instance()

		activity = self._model.get_activity(activity_id)
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
