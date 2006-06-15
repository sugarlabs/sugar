import pygtk
pygtk.require('2.0')
import gtk
import gobject

class WindowManager:
	__managers_list = []

	CENTER = 0
	LEFT = 1
	RIGHT = 2
	TOP = 3
	BOTTOM = 4
	
	ABSOLUTE = 0
	SCREEN_RELATIVE = 1
	
	VISIBLE = 0
	SLIDED_IN = 1
	HIDDEN = 2

	def __init__(self, window):
		self._window = window
		self._visibility = WindowManager.HIDDEN

		WindowManager.__managers_list.append(self)
		
		window.connect("key-press-event", self.__key_press_event_cb)
		window.connect("focus-in-event", self.__focus_in_event_cb)
		window.connect_after("focus-out-event", self.__focus_out_event_cb)

	def has_focus(self):
		return self._window.has_toplevel_focus()

	def _update_visibility(self):		
		visible = False
		
		if self._visibility is WindowManager.VISIBLE:
			visible = True
		elif self._visibility is WindowManager.HIDDEN:
			visible = False
		elif self._visibility is WindowManager.SLIDED_IN:
			for manager in WindowManager.__managers_list:
				if manager.has_focus():
					visible = True
		
		if self._window.get_property('visible') != visible:
			self._window.set_property('visible', visible)

	def __focus_change_idle(self):
		for manager in WindowManager.__managers_list:
			manager._update_visibility()
		return False

	def __focus_in_event_cb(self, window, event):
		gobject.idle_add(self.__focus_change_idle)
				
	def __focus_out_event_cb(self, window, event):
		gobject.idle_add(self.__focus_change_idle)
		
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
			width = int(screen_width * self._width)

		if self._height_type is WindowManager.ABSOLUTE:
			height = self._height			
		elif self._height_type is WindowManager.SCREEN_RELATIVE:
			height = int(screen_height * self._height)
			
		if self._position is WindowManager.CENTER:
			x = int((screen_width - width) / 2)
			y = int((screen_height - height) / 2)
		elif self._position is WindowManager.LEFT:
			x = 0
			y = int((screen_height - height) / 2)
		elif self._position is WindowManager.TOP:
			x = int((screen_width - width) / 2)
			y = 0
			
		self._window.move(x, y)
		self._window.resize(width, height)

	def slide_window_in(self):
		self._visibility = WindowManager.SLIDED_IN
		self._update_visibility()
	
	def slide_window_out(self):
		self._visibility = WindowManager.HIDDEN
		self._update_visibility()
	
	def show(self):
		self._visibility = WindowManager.VISIBLE
	
	def manage(self):
		self._update_size_and_position()
		self._update_visibility()
