import logging

import gtk

class Console(gtk.ScrolledWindow):
	def __init__(self):
		gtk.ScrolledWindow.__init__(self)

		self._show_debug = False

		self.set_policy(gtk.POLICY_AUTOMATIC,
					    gtk.POLICY_AUTOMATIC)

		self._textview = gtk.TextView()
		self._textview.set_wrap_mode(gtk.WRAP_WORD)
		self.add(self._textview)
		self._textview.show()

		buf = self._textview.get_buffer()
		self._debug_tag = buf.create_tag("debug")
		self._debug_tag.set_property("invisible", True)

	def get_show_debug(self):
		return self._show_debug

	def set_show_debug(self, show_debug):
		self._show_debug = show_debug
		self._debug_tag.set_property("invisible", not show_debug)

	def log(self, level, message):
		msg = message + '\n'
		buf = self._textview.get_buffer()
		it = buf.get_end_iter()

		if level == logging.DEBUG:
			buf.insert_with_tags(it, msg, self._debug_tag)
		else:
			buf.insert(it, msg)
		
class ConsoleWindow(gtk.Window):
	def __init__(self):
		gtk.Window.__init__(self)

		self.set_default_size(620, 440)
		self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
		self.set_title("Console")
		self.connect("delete_event", lambda w, e: w.hide_on_delete())

		vbox = gtk.VBox()

		toolbar = gtk.Toolbar()

		self._debug_toggle = gtk.ToggleToolButton()
		self._debug_toggle.connect('toggled', self.__debug_toggled_cb)
		self._debug_toggle.set_label('Debug')
		toolbar.insert(self._debug_toggle, -1)
		self._debug_toggle.show()

		vbox.pack_start(toolbar, False)
		toolbar.show()

		self._nb = gtk.Notebook()
		self._nb.connect('switch-page', self.__page_changed_cb)
		vbox.pack_start(self._nb)
		self._nb.show()

		self.add(vbox)
		vbox.show()

		self._consoles = {}

	def _add_console(self, page_id):
		console = Console()
		page = self._nb.append_page(console, gtk.Label(page_id))
		console.show()

		self._consoles[page_id] = console

		return console

	def _get_console(self, page_id):
		if not self._consoles.has_key(page_id):
			console = self._add_console(page_id)
		else:
			console = self._consoles[page_id]
		return console

	def __debug_toggled_cb(self, button):
		console = self._nb.get_nth_page(self._nb.get_current_page())
		console.set_show_debug(button.get_active())

	def __page_changed_cb(self, notebook, page, page_num):
		console = self._nb.get_nth_page(page_num)
		self._debug_toggle.set_active(console.get_show_debug())

	def set_page(self, page_id):
		page = self._nb.page_num(self._consoles[page_id])
		self._nb.set_current_page(page)

	def log(self, level, page_id, message):
		console = self._get_console(page_id)
		console.log(level, message)
