import gobject

class Timeline(gobject.GObject):
	__gsignals__ = {
		'next-frame':   (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([int])),
		'completed':   (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([]))
	}

	def __init__(self, stage, n_frames):
		gobject.GObject.__init__(self)

		self._stage = stage
		self._fps = stage.get_fps()
		self._n_frames = n_frames
		self._current_frame = 0

	def start(self):
		gobject.timeout_add(1000 / self._fps, self.__timeout_cb)

	def get_n_frames(self):
		return self._n_frames

	def __timeout_cb(self):
		self.emit('next-frame', self._current_frame)

		# FIXME skip frames if necessary
		self._current_frame += 1

		if self._current_frame < self._n_frames:
			return True
		else:
			self.emit('completed')
			return False
