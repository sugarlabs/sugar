import gtk

class Console(gtk.ScrolledWindow):
	def __init__(self):
		gtk.ScrolledWindow.__init__(self)
		self.set_policy(gtk.POLICY_AUTOMATIC,
					    gtk.POLICY_AUTOMATIC)
		
		self._textview = gtk.TextView()
		self._textview.set_wrap_mode(gtk.WRAP_WORD)
		self.add(self._textview)
		self._textview.show()

	def log(self, message):
		buf = self._textview.get_buffer()
		buf.insert(buf.get_end_iter(), message)
		
class ConsoleWindow(gtk.Window):
	def __init__(self):
		gtk.Window.__init__(self)

		self.set_default_size(620, 440)
		self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
		self.set_title("Console")
		self.connect("delete_event", lambda w, e: w.hide_on_delete())

		self._nb = gtk.Notebook()
		self.add(self._nb)
		self._nb.show()

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

	def set_page(self, page_id):
		page = self._nb.page_num(self._consoles[page_id])
		self._nb.set_current_page(page)

	def log(self, page_id, message):
		console = self._get_console(page_id)
		console.log(message)
