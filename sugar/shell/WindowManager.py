import pygtk
pygtk.require('2.0')
import gtk

class WindowManager:
	__managers_list = []

	CENTER = 0
	LEFT = 1
	RIGHT = 2
	BOTTOM = 3
	
	ABSOLUTE = 0
	SCREEN_RELATIVE = 1

	def __init__(self, window):
		self._window = window

		WindowManager.__managers_list.append(self)
		
		window.connect("key-press-event", self.__key_press_event_cb)

	def __key_press_event_cb(self, window, event):
		manager = None

		if event.keyval == gtk.keysyms.Left and \
		   event.state & gtk.gdk.CONTROL_MASK:
			for wm in WindowManager.__managers_list:
				if wm._position == WindowManager.LEFT:
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
	
	def _update_size_and_position(self):
		screen_width = self._window.get_screen().get_width()
		screen_height = self._window.get_screen().get_height()
		
		if self._width_type is WindowManager.ABSOLUTE:
			width = self._width			
		elif self._width_type is WindowManager.SCREEN_RELATIVE:
			width = screen_width * self._width

		if self._height_type is WindowManager.ABSOLUTE:
			height = self._height			
		elif self._height_type is WindowManager.SCREEN_RELATIVE:
			height = screen_height * self._height
			
		if self._position is WindowManager.CENTER:
			x = (screen_width - width) / 2
			y = (screen_height - height) / 2
		elif self._position is WindowManager.LEFT:
			x = 0
			y = (screen_height - height) / 2
			
		self._window.move(x, y)
		self._window.resize(width, height)
			
	def slide_window_in(self):
		self._window.show()
	
	def slide_window_out(self):
		self._window.hide()
		
	def show_window(self):
		self._update_size_and_position()
		self._window.show()
		
	def hide_window(self):
		self._window.hide()
