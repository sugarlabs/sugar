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

from gettext import gettext as _
import gobject, gtk

IW_AUTH_ALG_OPEN_SYSTEM = 0x00000001
IW_AUTH_ALG_SHARED_KEY  = 0x00000002

IW_AUTH_WPA_VERSION_DISABLED = 0x00000001
IW_AUTH_WPA_VERSION_WPA      = 0x00000002
IW_AUTH_WPA_VERSION_WPA2     = 0x00000004

NM_802_11_CAP_NONE            = 0x00000000
NM_802_11_CAP_PROTO_NONE      = 0x00000001
NM_802_11_CAP_PROTO_WEP       = 0x00000002
NM_802_11_CAP_PROTO_WPA       = 0x00000004
NM_802_11_CAP_PROTO_WPA2      = 0x00000008
NM_802_11_CAP_KEY_MGMT_PSK    = 0x00000040
NM_802_11_CAP_KEY_MGMT_802_1X = 0x00000080
NM_802_11_CAP_CIPHER_WEP40    = 0x00001000
NM_802_11_CAP_CIPHER_WEP104   = 0x00002000
NM_802_11_CAP_CIPHER_TKIP     = 0x00004000
NM_802_11_CAP_CIPHER_CCMP     = 0x00008000

NM_AUTH_TYPE_WPA_PSK_AUTO = 0x00000000
IW_AUTH_CIPHER_NONE   = 0x00000001
IW_AUTH_CIPHER_WEP40  = 0x00000002
IW_AUTH_CIPHER_TKIP   = 0x00000004
IW_AUTH_CIPHER_CCMP   = 0x00000008
IW_AUTH_CIPHER_WEP104 = 0x00000010

IW_AUTH_KEY_MGMT_802_1X	= 0x1
IW_AUTH_KEY_MGMT_PSK	= 0x2

def string_is_hex(key):
    is_hex = True
    for c in key:
        if not 'a' <= c.lower() <= 'f' and not '0' <= c <= '9':
            is_hex = False
    return is_hex

class KeyDialog(gtk.Dialog):
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
        #self._entry.props.visibility = False
        self._entry.connect('changed', self._update_response_sensitivity)
        self.vbox.pack_start(self._entry)
        self.vbox.set_spacing(6)
        self.vbox.show_all()

        self.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                         gtk.STOCK_OK, gtk.RESPONSE_OK)
        self.set_default_response(gtk.RESPONSE_OK)

        self._update_response_sensitivity()

        self._entry.grab_focus()
        self.set_has_separator(True)

    def create_security(self):
        raise NotImplementedError

    def get_network(self):
        return self._net

    def get_callbacks(self):
        return (self._async_cb, self._async_err_cb)

class WEPKeyDialog(KeyDialog):
    def __init__(self, net, async_cb, async_err_cb):
        KeyDialog.__init__(self, net, async_cb, async_err_cb)

        self.store = gtk.ListStore(str, int)
        self.store.append(["Open System", IW_AUTH_ALG_OPEN_SYSTEM])
        self.store.append(["Shared Key", IW_AUTH_ALG_SHARED_KEY])

        self.combo = gtk.ComboBox(self.store)
        cell = gtk.CellRendererText()
        self.combo.pack_start(cell, True)
        self.combo.add_attribute(cell, 'text', 0)
        self.combo.set_active(0)

        self.hbox = gtk.HBox()
        self.hbox.pack_start(gtk.Label(_("Authentication Type:")))
        self.hbox.pack_start(self.combo)
        self.hbox.show_all()

        self.vbox.pack_start(self.hbox)

    def create_security(self):
        key = self._entry.get_text()

        it = self.combo.get_active_iter()
        (auth_alg, ) = self.store.get(it, 1)

        we_cipher = None
        if len(key) == 26:
            we_cipher = IW_AUTH_CIPHER_WEP104
        elif len(key) == 10:
            we_cipher = IW_AUTH_CIPHER_WEP40

        from nminfo import Security
        return Security.new_from_args(we_cipher, (key, auth_alg))

    def _update_response_sensitivity(self, ignored=None):
        key = self._entry.get_text()
        is_hex = string_is_hex(key)
        valid_len = (len(key) == 10 or len(key) == 26)
        self.set_response_sensitive(gtk.RESPONSE_OK, is_hex and valid_len)

class WPAKeyDialog(KeyDialog):
    def __init__(self, net, async_cb, async_err_cb):
        KeyDialog.__init__(self, net, async_cb, async_err_cb)

        self.store = gtk.ListStore(str, int)
        self.store.append(["Automatic", NM_AUTH_TYPE_WPA_PSK_AUTO])
        if net.get_caps() & NM_802_11_CAP_CIPHER_CCMP:
            self.store.append(["AES-CCMP", IW_AUTH_CIPHER_CCMP])
        if net.get_caps() & NM_802_11_CAP_CIPHER_TKIP:
            self.store.append(["TKIP", IW_AUTH_CIPHER_TKIP])

        self.combo = gtk.ComboBox(self.store)
        cell = gtk.CellRendererText()
        self.combo.pack_start(cell, True)
        self.combo.add_attribute(cell, 'text', 0)
        self.combo.set_active(0)

        self.hbox = gtk.HBox()
        self.hbox.pack_start(gtk.Label(_("Encryption Type:")))
        self.hbox.pack_start(self.combo)
        self.hbox.show_all()

        self.vbox.pack_start(self.hbox)

    def create_security(self):
        ssid = self.get_network().get_ssid()
        key = self._entry.get_text()
        is_hex = string_is_hex(key)

        real_key = None
        if len(key) == 64 and is_hex:
            # Hex key
            real_key = key
        elif len(key) >= 8 and len(key) <= 63:
            # passphrase
            import commands
            (s, o) = commands.getstatusoutput("/usr/sbin/wpa_passphrase '%s' '%s'" % (ssid, key))
            if s != 0:
                raise RuntimeError("Error hashing passphrase: %s" % o)
            lines = o.split("\n")
            for line in lines:
                if line.strip().startswith("psk="):
                    real_key = line.strip()[4:]
            if real_key and len(real_key) != 64:
                real_key = None

        if not real_key:
            raise RuntimeError("Invalid key")

        it = self.combo.get_active_iter()
        (we_cipher, ) = self.store.get(it, 1)

        wpa_ver = IW_AUTH_WPA_VERSION_WPA
        caps = self.get_network().get_caps()
        if caps & NM_802_11_CAP_PROTO_WPA2:
            wpa_ver = IW_AUTH_WPA_VERSION_WPA2

        from nminfo import Security
        return Security.new_from_args(we_cipher, (real_key, wpa_ver, IW_AUTH_KEY_MGMT_PSK))

    def _update_response_sensitivity(self, ignored=None):
        key = self._entry.get_text()
        is_hex = string_is_hex(key)

        valid = False
        if len(key) == 64 and is_hex:
            # hex key
            valid = True
        elif len(key) >= 8 and len(key) <= 63:
            # passphrase
            valid = True
        self.set_response_sensitive(gtk.RESPONSE_OK, valid)
        return False

def new_key_dialog(net, async_cb, async_err_cb):
    caps = net.get_caps()
    if (caps & NM_802_11_CAP_CIPHER_TKIP or caps & NM_802_11_CAP_CIPHER_CCMP) and \
            (caps & NM_802_11_CAP_PROTO_WPA or caps & NM_802_11_CAP_PROTO_WPA2):
        return WPAKeyDialog(net, async_cb, async_err_cb)
    elif (caps & NM_802_11_CAP_CIPHER_WEP40 or caps & NM_802_11_CAP_CIPHER_WEP104) and \
            (caps & NM_802_11_CAP_PROTO_WEP):
        return WEPKeyDialog(net, async_cb, async_err_cb)
    else:
        raise RuntimeError("Unhandled network capabilities %x" % caps)



class FakeNet(object):
    def get_ssid(self):
        return "olpcwpa"

    def get_caps(self):
#        return NM_802_11_CAP_CIPHER_WEP104 | NM_802_11_CAP_PROTO_WEP
        return NM_802_11_CAP_CIPHER_CCMP | NM_802_11_CAP_CIPHER_TKIP | NM_802_11_CAP_PROTO_WPA

def response_cb(widget, response_id):
    if response_id == gtk.RESPONSE_OK:
        print dialog.get_options()
    else:
        print "canceled"
    widget.hide()
    widget.destroy()


if __name__ == "__main__":
    net = FakeNet()
    dialog = new_key_dialog(net, None, None)
    dialog.connect("response", response_cb)
    dialog.run()

