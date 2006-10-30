# Copyright (C) 2006, Red Hat, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

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
		except AttributeError:
			method = None

		if method:
			method(current_frame, n_frames)

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

	def goto(self, tag_name, end_frame=False):
		self.pause()

		tag = self._name_to_tag[tag_name]
		if end_frame:
			self._current_frame = tag.end_frame
		else:
			self._current_frame = tag.start_frame

		self._next_frame(tag, self._current_frame)

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
		self.pause()

		if start_tag == None:
			start = 0
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

	def pause(self):
		if self._timeout_sid > 0:
			gobject.source_remove(self._timeout_sid)
