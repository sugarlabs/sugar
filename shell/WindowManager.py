import time
import logging

import gtk
import gobject

DEFAULT_WIDTH = 640
DEFAULT_HEIGHT = 480

SLIDING_TIME = 0.8

class SlidingHelper:
	IN = 0
	OUT = 1

	def __init__(self, manager, direction):
		self._direction = direction
		self._cur_time = time.time()
		self._target_time = self._cur_time + SLIDING_TIME
		self._manager = manager
		self._start = True
		self._end = False

		(x, y, width, height) = manager.get_geometry()
		self._orig_y = y
		if direction == SlidingHelper.IN:
			self._target_y = y
			manager.set_geometry(x, y - height, width, height)
		else:
			self._target_y = y - height

	def get_direction(self):
		return self._direction

	def is_start(self):
		return self._start

	def is_end(self):
		return self._end

	def get_next_y(self):
		self._start = False
	
		(x, y, width, height) = self._manager.get_geometry()

		old_time = self._cur_time
		self._cur_time = time.time()
		remaining = self._target_time - self._cur_time

		if remaining <= 0 or \
		   (y > self._target_y and self._direction == SlidingHelper.IN) or \
		   (y < self._target_y and self._direction == SlidingHelper.OUT):
			self._end = True
			y = self._orig_y
		else:
			approx_time_step = float(self._cur_time - old_time)
			approx_n_steps = remaining / approx_time_step
			step = (self._target_y - y) / approx_n_steps
			y += step
		
		return y

class WindowManager:
	__managers_list = []

	TYPE_ACTIVITY = 0
	TYPE_POPUP    = 1 

	ANIMATION_NONE     = 0
	ANIMATION_SLIDE_IN = 1

	def __init__(self, window):
		self._window = window
		self._window_type = WindowManager.TYPE_ACTIVITY
		self._animation = WindowManager.ANIMATION_NONE
		self._key = 0
		self._animating = False

		window.connect("key-press-event", self.__key_press_event_cb)

		WindowManager.__managers_list.append(self)

	def __key_press_event_cb(self, window, event):
		# FIXME we should fix this to work also while animating
		if self._animating:
			return False
	
		for manager in WindowManager.__managers_list:
			if event.keyval == manager._key:
				if manager._window.get_property('visible'):
					manager.hide()
				else:
					manager.show()

	def get_geometry(self):
		return (self._x, self._y, self._width, self._height)

	def set_geometry(self, x, y, width, height):
		if self._window_type == WindowManager.TYPE_ACTIVITY:
			logging.error('The geometry will be ignored for activity windows')
	
		self._x = x
		self._y = y
		self._width = width
		self._height = height

	def set_animation(self, animation):
		self._animation = animation
	
	def set_type(self, window_type):
		self._window_type = window_type	

	def set_key(self, key):
		self._key = key

	def show(self):
		self._update_hints()
		self._update_size()

		if self._animation == WindowManager.ANIMATION_SLIDE_IN:
			self._slide_in()
		else:
			self._update_position()
			self._window.show()
	
	def hide(self):
		if self._animation == WindowManager.ANIMATION_SLIDE_IN:
			self._slide_out()
		else:
			self._window.hide()

	def _get_screen_dimensions(self):
		screen_width = DEFAULT_WIDTH
		screen_height = DEFAULT_HEIGHT
		
		for manager in WindowManager.__managers_list:
			if manager._window_type == WindowManager.TYPE_ACTIVITY:
				screen_width = manager._window.allocation.width
				screen_height = manager._window.allocation.height
		
		return (screen_width, screen_height)

	def _get_screen_position(self):
		result = (0, 0)		
		for manager in WindowManager.__managers_list:
			if manager._window_type == WindowManager.TYPE_ACTIVITY:
				result = manager._window.get_position()
		
		return result

	def _transform_position(self):
		(screen_width, screen_height) = self._get_screen_dimensions()
		(screen_x, screen_y) = self._get_screen_position()
		
		x = int(screen_width * self._x) + screen_x
		y = int(screen_height * self._y) + screen_y
		
		return (x, y)

	def _transform_dimensions(self):
		(screen_width, screen_height) = self._get_screen_dimensions()
	
		width = int(screen_width * self._width)
		height = int(screen_height * self._height)
		
		return (width, height)

	def _update_hints(self):
		if self._window_type == WindowManager.TYPE_POPUP:
			self._window.set_decorated(False)
			self._window.set_skip_taskbar_hint(True)

	def _update_size(self):
		if self._window_type == WindowManager.TYPE_ACTIVITY:
			self._window.resize(DEFAULT_WIDTH, DEFAULT_HEIGHT)
		else:
			(width, height) = self._transform_dimensions()
			self._window.resize(width, height)

	def _update_position(self):
		if self._window_type == WindowManager.TYPE_POPUP:
			(x, y) = self._transform_position()
			self._window.move(x, y)

	def __slide_timeout_cb(self, helper):
		start = helper.is_start()

		self._y = helper.get_next_y()
		self._update_position()
		
		if start and helper.get_direction() == SlidingHelper.IN:
			self._window.show()
		elif helper.is_end() and helper.get_direction() == SlidingHelper.OUT:
			self._window.hide()

		self._animating = not helper.is_end()
				
		return not helper.is_end()

	def _slide_in(self):
		helper = SlidingHelper(self, SlidingHelper.IN)
		gobject.idle_add(self.__slide_timeout_cb, helper)
		
	def _slide_out(self):
		helper = SlidingHelper(self, SlidingHelper.OUT)
		gobject.idle_add(self.__slide_timeout_cb, helper)
