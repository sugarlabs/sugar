import pygtk
pygtk.require('2.0')
import gtk
import gobject

SM_SPACE_PROPORTIONAL = 0
SM_STEP = 1

SLIDING_TIMEOUT = 50
SLIDING_MODE = SM_SPACE_PROPORTIONAL

#SLIDING_TIMEOUT = 10
#SLIDING_MODE = SM_STEP
#SLIDING_STEP = 0.05

class WindowManager:
	__managers_list = []

	CENTER = 0
	LEFT = 1
	RIGHT = 2
	TOP = 3
	BOTTOM = 4
	
	ABSOLUTE = 0
	SCREEN_RELATIVE = 1
	
	def __init__(self, window):
		self._window = window
		self._sliding_pos = 0

		WindowManager.__managers_list.append(self)
		
		window.connect("key-press-event", self.__key_press_event_cb)

	def __key_press_event_cb(self, window, event):
		manager = None

		if event.keyval == gtk.keysyms.Left and \
		   event.state & gtk.gdk.CONTROL_MASK:
			for wm in WindowManager.__managers_list:
				if wm._position == WindowManager.LEFT:
					manager = wm

		if event.keyval == gtk.keysyms.Up and \
		   event.state & gtk.gdk.CONTROL_MASK:
			for wm in WindowManager.__managers_list:
				if wm._position == WindowManager.TOP:
					manager = wm

		if event.keyval == gtk.keysyms.Down and \
		   event.state & gtk.gdk.CONTROL_MASK:
			for wm in WindowManager.__managers_list:
				if wm._position == WindowManager.BOTTOM:
					manager = wm

		if manager and manager._window.get_property('visible'):
			manager.slide_window_out()
		elif manager:
			manager.slide_window_in()
	
	def set_width(self, width, width_type):
		self._width = width
		self._width_type = width_type

	def set_height(self, height, height_type):
		self._height = height
		self._height_type = height_type
	
	def set_position(self, position):
		self._position = position

	def _update_size(self):
		screen_width = self._window.get_screen().get_width()
		screen_height = self._window.get_screen().get_height()
		
		if self._width_type is WindowManager.ABSOLUTE:
			width = self._width			
		elif self._width_type is WindowManager.SCREEN_RELATIVE:
			width = int(screen_width * self._width)

		if self._height_type is WindowManager.ABSOLUTE:
			height = self._height			
		elif self._height_type is WindowManager.SCREEN_RELATIVE:
			height = int(screen_height * self._height)
			
		self._real_width = width
		self._real_height = height

		self._window.set_size_request(self._real_width,
									  self._real_height)

	def _update_position(self):
		screen_width = self._window.get_screen().get_width()
		screen_height = self._window.get_screen().get_height()
		
		width = self._real_width
		height = self._real_height
		
		if self._position is WindowManager.CENTER:
			self._x = int((screen_width - width) / 2)
			self._y = int((screen_height - height) / 2)
		elif self._position is WindowManager.LEFT:
			self._x = - int((1.0 - self._sliding_pos) * width)
			self._y = int((screen_height - height) / 2)
		elif self._position is WindowManager.TOP:
			self._x = int(screen_width - width - 10)
			self._y = - int((1.0 - self._sliding_pos) * height)
		elif self._position is WindowManager.BOTTOM:
			self._x = int((screen_width - width) / 2)
			self._y = screen_height - int(self._sliding_pos * height)
	
		self._window.move(self._x, self._y)

	def __slide_in_timeout_cb(self):
		if self._sliding_pos == 0:
			self._window.show()

		if SLIDING_MODE == SM_SPACE_PROPORTIONAL:
			space_to_go = 1.0 - self._sliding_pos
			self._sliding_pos += (space_to_go / 2)
		else:
			self._sliding_pos += SLIDING_STEP

		if self._sliding_pos > .999:
			self._sliding_pos = 1.0

		self._update_position()

		if self._sliding_pos == 1.0:
			return False
		else:
			return True

	def __slide_out_timeout_cb(self):
		if SLIDING_MODE == SM_SPACE_PROPORTIONAL:
			space_to_go = self._sliding_pos
			self._sliding_pos -= (space_to_go / 2)
		else:
			self._sliding_pos -= SLIDING_STEP

		if self._sliding_pos < .001:
			self._sliding_pos = 0

		self._update_position()

		if self._sliding_pos == 0:
			self._window.hide()
			return False
		else:
			return True

	def slide_window_in(self):
		self._sliding_pos = 0
		gobject.timeout_add(SLIDING_TIMEOUT, self.__slide_in_timeout_cb)
		
	def slide_window_out(self):
		self._sliding_pos = 1.0
		gobject.timeout_add(SLIDING_TIMEOUT, self.__slide_out_timeout_cb)
			
	def show(self):
		self._window.show()

	def update(self):
		self._update_position()
	
	def manage(self):
		self._update_size()
		self._update_position()
