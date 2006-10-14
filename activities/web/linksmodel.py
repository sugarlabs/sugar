# Copyright (C) 2006, Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import gobject

class Link(object):
	def __init__(self, buddy, title, url):
		self.buddy = buddy
		self.title = title
		self.url = url

class LinksModel(gobject.GObject):
	__gsignals__ = {
		'link-added':   (gobject.SIGNAL_RUN_FIRST,
						 gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT])),
		'link-removed': (gobject.SIGNAL_RUN_FIRST,
						 gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT])),
	}

	def __init__(self):
		gobject.GObject.__init__(self)
		self._links = {}

	def add_link(self, buddy, title, url):
		link = Link(buddy, title, url)
		self._links[(buddy.get_name(), url)] = link

		self.emit('link-added', link)

	def remove_link(self, buddy, url):
		key = (buddy.get_name(), url)
		if self._links.haskey(key):
			link = self._links[key]
			del self._links[key]
			self.emit('link-removed', link)

	def __iter__(self):
		return self._links.values().__iter__()
