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

	def add_link(buddy, title, url):
		link = Link(buddy, title, url)
		self._links[(buddy.get_name(), url)] = link

		self.emit('link-added', link)

	def remove_link(buddy, url):
		key = (buddy.get_name(), url)
		if self._links.haskey(key):
			link = self._links[key]
			del self._links[key]
			self.emit('link-removed', link)

	def __iter__(self):
		return self._links.values().__iter__()
