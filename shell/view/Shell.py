import gtk
import gobject
import wnck

from view.home.HomeWindow import HomeWindow
from view.ActivityHost import ActivityHost
from view.frame.Frame import Frame
from globalkeys import KeyGrabber
import sugar

class Shell(gobject.GObject):
	def __init__(self, model):
		gobject.GObject.__init__(self)

		self._model = model
		self._screen = wnck.screen_get_default()

		self._key_grabber = KeyGrabber()
		self._key_grabber.connect('key-pressed', self.__global_key_pressed_cb)
		self._key_grabber.grab('F1')
		self._key_grabber.grab('F2')
		self._key_grabber.grab('F3')
		self._key_grabber.grab('F4')
		self._key_grabber.grab('F5')
		self._key_grabber.grab('F6')

		self._home_window = HomeWindow(self.get_model())
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
			self._model.start_activity('org.sugar.Terminal')

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

	def set_zoom_level(self, level):
		if level == sugar.ZOOM_ACTIVITY:
			self._screen.toggle_showing_desktop(False)
		else:
			self._screen.toggle_showing_desktop(True)
			self._home_window.set_zoom_level(level)
