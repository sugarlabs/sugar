import gtk

from gettext import gettext as _

import conf

class FirstTimeDialog(gtk.Dialog):
	def __init__(self):
		gtk.Dialog.__init__(self)

		label = gtk.Label(_('Nick Name:'))
		label.set_alignment(0.0, 0.5)
		self.vbox.pack_start(label)
		label.show()

		self._entry = gtk.Entry()
		self._entry.connect('changed', self._entry_changed_cb)
		self.vbox.pack_start(self._entry)
		self._entry.show()

		self._ok = gtk.Button(None, gtk.STOCK_OK)
		self._ok.set_sensitive(False)
		self.vbox.pack_start(self._ok)
		self._ok.connect('clicked', self.__ok_button_clicked_cb)
		self._ok.show()

	def _entry_changed_cb(self, entry):
		valid = (len(entry.get_text()) > 0)
		self._ok.set_sensitive(valid)

	def __ok_button_clicked_cb(self, button):
		profile = conf.get_profile()
		profile.set_nick_name(self._entry.get_text())
		self.destroy()

def get_profile():
	profile = conf.get_profile()
	if profile.get_nick_name() == None:
		dialog = FirstTimeDialog()
		dialog.connect('destroy', self.__first_time_dialog_destroy_cb)
		dialog.show()
	return profile
