# vi: ts=4 ai noet
#
# Copyright (C) 2006-2007 Red Hat, Inc.
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

import gtk

IW_AUTH_ALG_OPEN_SYSTEM = 0x00000001
IW_AUTH_ALG_SHARED_KEY  = 0x00000002

class WEPKeyDialog(gtk.Dialog):
    def __init__(self, net, async_cb, async_err_cb):
        gtk.Dialog.__init__(self, flags=gtk.DIALOG_MODAL)
        self.set_title("Wireless Key Required")

        self._net = net
        self._async_cb = async_cb
        self._async_err_cb = async_err_cb

        self.set_has_separator(False)        

        label = gtk.Label("A wireless encryption key is required for\n" \
            " the wireless network '%s'." % net.get_ssid())
        self.vbox.pack_start(label)

        self._entry = gtk.Entry()
        self._entry.props.visibility = False
        self._entry.connect('changed', self._entry_changed_cb)
        self.vbox.pack_start(self._entry)
        self.vbox.show_all()

        self.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                         gtk.STOCK_OK, gtk.RESPONSE_OK)

        self.set_default_response(gtk.RESPONSE_OK)
        self._update_response_sensitivity()

        self._entry.grab_focus()

    def get_key(self):
        return self._entry.get_text()

    def get_auth_alg(self):
        return IW_AUTH_ALG_OPEN_SYSTEM

    def get_network(self):
        return self._net

    def get_callbacks(self):
        return (self._async_cb, self._async_err_cb)

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
