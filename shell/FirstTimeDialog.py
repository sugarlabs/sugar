import gtk

from gettext import gettext as _

from sugar import conf

class FirstTimeDialog(gtk.Window):
	def __init__(self):
		gtk.Window.__init__(self)

		self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)

		vbox = gtk.VBox(False, 6)
		vbox.set_border_width(12)

		label = gtk.Label(_('Nick Name:'))
		label.set_alignment(0.0, 0.5)
		vbox.pack_start(label)
		label.show()

		self._entry = gtk.Entry()
		vbox.pack_start(self._entry)
		self._entry.show()

		button = gtk.Button(None, gtk.STOCK_OK)
		vbox.pack_start(button)
		button.connect('clicked', self.__ok_button_clicked_cb)
		button.show()

		self.add(vbox)
		vbox.show()

	def __ok_button_clicked_cb(self, button):
		profile = conf.get_profile()
		profile.set_nick_name(self._entry.get_text())
		self.destroy()
