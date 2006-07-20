import gtk

class ConsoleWindow(gtk.Window):
	def __init__(self):
		gtk.Window.__init__(self)

		self.set_default_size(620, 440)
		self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
		self.set_title("Console")
		self.connect("delete_event", lambda w, e: w.hide_on_delete())

		sw = gtk.ScrolledWindow()
		sw.set_policy(gtk.POLICY_AUTOMATIC,
					  gtk.POLICY_AUTOMATIC)
		
		self._console = gtk.TextView()
		self._console.set_wrap_mode(gtk.WRAP_WORD)
		sw.add(self._console)
		self._console.show()
		
		self.add(sw)
		sw.show()

	def log(self, message):
		buf = self._console.get_buffer() 
		buf.insert(buf.get_end_iter(), message)
