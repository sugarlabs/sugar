import gobject

class _Tag:
	def __init__(self, name, start_frame, end_frame):
		self.name = name
		self.start_frame = start_frame
		self.end_frame = end_frame

class TimelineObserver:
	def __init__(self, observer):
		self._observer = observer

	def next_frame(self, tag, current_frame, n_frames):
		try:
			method = getattr(self._observer, 'do_' + tag)
			method(current_frame, n_frames)
		except:
			pass

class Timeline:
	def __init__(self, observer):
		self._fps = 12
		self._tags = []
		self._name_to_tag = {}
		self._current_frame = 0
		self._timeout_sid = 0
		self._observer = TimelineObserver(observer)

	def add_tag(self, name, start_frame, end_frame):
		tag = _Tag(name, start_frame, end_frame)
		self._tags.append(tag)
		self._name_to_tag[name] = tag 

	def remove_tag(self, name):
		tag = self._tags[name]
		self._tags.remove(tag)
		del self._tags[name]

	def _next_frame(self, tag, frame):
		n_frames = tag.start_frame - tag.end_frame
		self._observer.next_frame(tag.name, frame, n_frames)

	def on_tag(self, name):
		tag = self._name_to_tag[name]
		return (tag.start_frame <= self._current_frame and \
				tag.end_frame >= self._current_frame)

	def _get_tags_for_frame(self, frame):
		result = []
		for tag in self._tags:
			if tag.start_frame <= frame and tag.end_frame >= frame:
				result.append(tag)
		return result

	def _timeout_cb(self, end_frame):
		for tag in self._get_tags_for_frame(self._current_frame):
			cur_frame = self._current_frame - tag.start_frame
			self._next_frame(tag, cur_frame)

		if self._current_frame < end_frame:
			self._current_frame += 1
			return True
		else:
			return False

	def play(self, start_tag=None, stop_tag=None):
		self.stop()

		if start_tag == None:
			start = self._tags[0].start_frame
		else:
			start = self._name_to_tag[start_tag].start_frame

		if stop_tag == None:
			end = self._tags[len(self._tags) - 1].end_frame
		else:
			end = self._name_to_tag[stop_tag].end_frame

		self._current_frame = start

		interval = 1000 / self._fps
		self._timeout_sid = gobject.timeout_add(
						interval, self._timeout_cb, end)

	def stop(self):
		if self._timeout_sid > 0:
			gobject.source_remove(self._timeout_sid)
