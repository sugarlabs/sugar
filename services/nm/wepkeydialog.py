import gtk

class WEPKeyDialog(gtk.Dialog):
	def __init__(self):
		gtk.Dialog.__init__(self)

		self.set_has_separator(False)		

		self._entry = gtk.Entry()
		self._entry.props.visibility = False
		self._entry.connect('changed', self._entry_changed_cb)
		self.vbox.pack_start(self._entry)
		self._entry.show()

		self.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
						 gtk.STOCK_OK, gtk.RESPONSE_OK)

		self.set_default_response(gtk.RESPONSE_OK)
		self._update_response_sensitivity()

	def get_key(self):
		return self._entry.get_text()

	def _entry_changed_cb(self, entry):
		self._update_response_sensitivity()

	def _update_response_sensitivity(self):
		key = self.get_key()

		is_hex = True
		for c in key:
			if not 'a' <= c <= 'f' and not '0' <= c <= '9':
				is_hex = False

		valid_len = (len(key) == 10 or len(key) == 26)
	 	self.set_response_sensitive(gtk.RESPONSE_OK, is_hex and valid_len)

if __name__ == "__main__":
	dialog = WEPKeyDialog()
	dialog.run()

	print dialog.get_key()
