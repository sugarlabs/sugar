import gtk

from _sugar import AddressEntry

class Toolbar(gtk.Toolbar):
	def __init__(self, embed):
		gtk.Toolbar.__init__(self)
		
		self.set_style(gtk.TOOLBAR_BOTH_HORIZ)

		self._insert_spring()

		self._back = gtk.ToolButton()
		self._back.props.sensitive = False
		self._back.set_icon_name('stock-back')
		self._back.connect("clicked", self._go_back_cb)
		self.insert(self._back, -1)
		self._back.show()

		self._forward = gtk.ToolButton()
		self._forward.props.sensitive = False
		self._forward.set_icon_name('stock-forward')
		self._forward.connect("clicked", self._go_forward_cb)
		self.insert(self._forward, -1)
		self._forward.show()

		separator = gtk.SeparatorToolItem()
		separator.set_draw(False)		
		self.insert(separator, -1)
		separator.show()

		address_item = gtk.ToolItem()

		self._entry = AddressEntry()
		self._entry.connect("activate", self._entry_activate_cb)

		width = int(gtk.gdk.screen_width() / 3 * 2)
		self._entry.set_size_request(width, -1)

		address_item.add(self._entry)
		self._entry.show()

		self.insert(address_item, -1)
		address_item.show()

		separator = gtk.SeparatorToolItem()
		separator.set_draw(False)		
		self.insert(separator, -1)
		separator.show()

		self._post = gtk.ToolButton()
		self._post.props.sensitive = False
		self._post.set_icon_name('stock-add')
		self._post.connect("clicked", self._post_cb)
		self.insert(self._post, -1)
		self._post.show()

		self._insert_spring()

		self._embed = embed
		self._embed.connect("notify::progress", self._progress_changed_cb)
		self._embed.connect("notify::address", self._address_changed_cb)
		self._embed.connect("notify::can-go-back",
							self._can_go_back_changed_cb)
		self._embed.connect("notify::can-go-forward",
							self._can_go_forward_changed_cb)

	def set_links_controller(self, links_controller):
		self._links_controller = links_controller
		self._post.props.sensitive = True

	def _progress_changed_cb(self, embed, spec):
		self._entry.props.progress = embed.props.progress

	def _address_changed_cb(self, embed, spec):
		self._entry.set_text(embed.props.address)

	def _can_go_back_changed_cb(self, embed, spec):
		self._back.props.sensitive = embed.props.can_go_back

	def _can_go_forward_changed_cb(self, embed, spec):
		self._forward.props.sensitive = embed.props.can_go_forward

	def _entry_activate_cb(self, entry):
		self._embed.load_url(entry.get_text())

	def _go_back_cb(self, button):
		self._embed.go_back()
	
	def _go_forward_cb(self, button):
		self._embed.go_forward()

	def _post_cb(self, button):
		title = self._embed.get_title()
		address = self._embed.get_location()
		self._links_controller.post_link(title, address)

	def _insert_spring(self):
		separator = gtk.SeparatorToolItem()
		separator.set_draw(False)
		separator.set_expand(True)		
		self.insert(separator, -1)
		separator.show()
