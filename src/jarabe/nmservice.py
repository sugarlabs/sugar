# Copyright (C) 2006-2008 Red Hat, Inc.
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

import logging
import md5
from gettext import gettext as _

import dbus.service
import gtk

from jarabe.model import network

NM_INFO_IFACE = 'org.freedesktop.NetworkManagerInfo'
NM_INFO_PATH = '/org/freedesktop/NetworkManagerInfo'

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

IW_AUTH_KEY_MGMT_802_1X = 0x1
IW_AUTH_KEY_MGMT_PSK    = 0x2

WEP_PASSPHRASE = 1
WEP_HEX = 2
WEP_ASCII = 3

class NoNetworks(dbus.DBusException):
    def __init__(self):
        dbus.DBusException.__init__(self)
        self._dbus_error_name = NM_INFO_IFACE + '.NoNetworks'

class CanceledKeyRequestError(dbus.DBusException):
    def __init__(self):
        dbus.DBusException.__init__(self)
        self._dbus_error_name = NM_INFO_IFACE + '.CanceledError'

class NMService(dbus.service.Object):
    def __init__(self):
        self._nmclient = network.get_manager()
        self._nminfo = self._nmclient.nminfo
        self._key_dialog = None
        bus = dbus.SystemBus()

        # If NMI is already around, don't grab the NMI service
        bus_object = bus.get_object('org.freedesktop.DBus',
                                    '/org/freedesktop/DBus')
        name = None
        try:
            name = bus_object.GetNameOwner( \
                    "org.freedesktop.NetworkManagerInfo",
                    dbus_interface='org.freedesktop.DBus')
        except dbus.DBusException:
            logging.debug("Error getting owner of NMI")
        if name:
            logging.info("NMI service already owned by %s, won't claim it."
                          % name)

        bus_name = dbus.service.BusName(NM_INFO_IFACE, bus=bus)
        dbus.service.Object.__init__(self, bus_name, NM_INFO_PATH)

    @dbus.service.method(NM_INFO_IFACE, in_signature='i', out_signature='as')
    def getNetworks(self, net_type):
        ssids = self._nminfo.get_networks(net_type)
        if len(ssids) > 0:
            return dbus.Array(ssids)

        raise NoNetworks()

    @dbus.service.method(NM_INFO_IFACE, in_signature='si',
                         async_callbacks=('async_cb', 'async_err_cb'))
    def getNetworkProperties(self, ssid, net_type, async_cb, async_err_cb):
        self._nminfo.get_network_properties(ssid, net_type,
                                            async_cb, async_err_cb)

    @dbus.service.method(NM_INFO_IFACE)
    def updateNetworkInfo(self, ssid, bauto, bssid, cipher, *args):
        self._nminfo.update_network_info(ssid, bauto, bssid, cipher, args)

    @dbus.service.method(NM_INFO_IFACE,
                         async_callbacks=('async_cb', 'async_err_cb'))
    def getKeyForNetwork(self, dev_path, net_path, ssid, attempt,
                         new_key, async_cb, async_err_cb):
        self._get_key_for_network(dev_path, net_path, ssid,
                                  attempt, new_key, async_cb, async_err_cb)

    @dbus.service.method(NM_INFO_IFACE)
    def cancelGetKeyForNetwork(self):
        self._cancel_get_key_for_network()

    def _get_key_for_network(self, dev_op, net_op, ssid, attempt,
                             new_key, async_cb, async_err_cb):
        if not isinstance(ssid, unicode):
            raise ValueError("Invalid arguments; ssid must be unicode.")
        if self._nminfo.allowed_networks.has_key(ssid) and not new_key:
            # We've got the info already
            net = self._nminfo.allowed_networks[ssid]
            async_cb(tuple(net.get_security()))
            return

        # Otherwise, ask the user for it
        net = None
        dev = self._nmclient.get_device(dev_op)
        if not dev:
            async_err_cb(network.NotFoundError("Device was unknown."))
            return

        if dev.get_type() == network.DEVICE_TYPE_802_3_ETHERNET:
            # We don't support wired 802.1x yet...
            async_err_cb(network.UnsupportedError(
                                "Device type is unsupported by NMI."))
            return

        net = dev.get_network(net_op)
        if not net:
            async_err_cb(network.NotFoundError("Network was unknown."))
            return

        self._key_dialog = new_key_dialog(net, async_cb, async_err_cb)
        self._key_dialog.connect("response", self._key_dialog_response_cb)
        self._key_dialog.connect("destroy", self._key_dialog_destroy_cb)
        self._key_dialog.show_all()

    def _key_dialog_destroy_cb(self, widget, data=None):
        if widget != self._key_dialog:
            return
        self._key_dialog_response_cb(widget, gtk.RESPONSE_CANCEL)

    def _key_dialog_response_cb(self, widget, response_id):
        if widget != self._key_dialog:
            return

        (async_cb, async_err_cb) = self._key_dialog.get_callbacks()
        security = None
        if response_id == gtk.RESPONSE_OK:
            security = self._key_dialog.create_security()
        self._key_dialog = None
        widget.destroy()

        if response_id in [gtk.RESPONSE_CANCEL, gtk.RESPONSE_NONE]:
            # key dialog dialog was canceled; send the error back to NM
            async_err_cb(CanceledKeyRequestError())
        elif response_id == gtk.RESPONSE_OK:
            if not security:
                raise RuntimeError("Invalid security arguments.")
            props = security.get_properties()
            a = tuple(props)
            async_cb(*a)
        else:
            raise RuntimeError("Unhandled key dialog response %d" % response_id)

    def _cancel_get_key_for_network(self):
        # Close the wireless key dialog and just have it return
        # with the 'canceled' argument set to true
        if not self._key_dialog:
            return
        self._key_dialog_destroy_cb(self._key_dialog)

def string_is_hex(key):
    is_hex = True
    for c in key:
        if not 'a' <= c.lower() <= 'f' and not '0' <= c <= '9':
            is_hex = False
    return is_hex

def string_is_ascii(string):
    try:
        string.encode('ascii')
        return True
    except UnicodeEncodeError:
        return False

def string_to_hex(passphrase):
    key = ''
    for c in passphrase:
        key += '%02x' % ord(c)
    return key

def hash_passphrase(passphrase):
    # passphrase must have a length of 64
    if len(passphrase) > 64:
        passphrase = passphrase[:64]
    elif len(passphrase) < 64:
        while len(passphrase) < 64:
            passphrase += passphrase[:64 - len(passphrase)]
    passphrase = md5.new(passphrase).digest()
    return string_to_hex(passphrase)[:26]

class KeyDialog(gtk.Dialog):
    def __init__(self, net, async_cb, async_err_cb):
        gtk.Dialog.__init__(self, flags=gtk.DIALOG_MODAL)
        self.set_title("Wireless Key Required")

        self._net = net
        self._async_cb = async_cb
        self._async_err_cb = async_err_cb
        self._entry = None

        self.set_has_separator(False)        

        label = gtk.Label("A wireless encryption key is required for\n" \
                          " the wireless network '%s'." % net.get_ssid())
        self.vbox.pack_start(label)

        self.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                         gtk.STOCK_OK, gtk.RESPONSE_OK)
        self.set_default_response(gtk.RESPONSE_OK)
        self.set_has_separator(True)

    def add_key_entry(self):
        self._entry = gtk.Entry()
        #self._entry.props.visibility = False
        self._entry.connect('changed', self._update_response_sensitivity)
        self._entry.connect('activate', self._entry_activate_cb)
        self.vbox.pack_start(self._entry)
        self.vbox.set_spacing(6)
        self.vbox.show_all()

        self._update_response_sensitivity()
        self._entry.grab_focus()

    def _entry_activate_cb(self, entry):
        self.response(gtk.RESPONSE_OK)

    def create_security(self):
        raise NotImplementedError

    def get_network(self):
        return self._net

    def get_callbacks(self):
        return (self._async_cb, self._async_err_cb)

class WEPKeyDialog(KeyDialog):
    def __init__(self, net, async_cb, async_err_cb):
        KeyDialog.__init__(self, net, async_cb, async_err_cb)

        # WEP key type
        self.key_store = gtk.ListStore(str, int)
        self.key_store.append(["Passphrase (128-bit)", WEP_PASSPHRASE])
        self.key_store.append(["Hex (40/128-bit)", WEP_HEX])
        self.key_store.append(["ASCII (40/128-bit)", WEP_ASCII])

        self.key_combo = gtk.ComboBox(self.key_store)
        cell = gtk.CellRendererText()
        self.key_combo.pack_start(cell, True)
        self.key_combo.add_attribute(cell, 'text', 0)
        self.key_combo.set_active(0)
        self.key_combo.connect('changed', self._key_combo_changed_cb)

        hbox = gtk.HBox()
        hbox.pack_start(gtk.Label(_("Key Type:")))
        hbox.pack_start(self.key_combo)
        hbox.show_all()
        self.vbox.pack_start(hbox)

        # Key entry field
        self.add_key_entry()

        # WEP authentication mode
        self.auth_store = gtk.ListStore(str, int)
        self.auth_store.append(["Open System", IW_AUTH_ALG_OPEN_SYSTEM])
        self.auth_store.append(["Shared Key", IW_AUTH_ALG_SHARED_KEY])

        self.auth_combo = gtk.ComboBox(self.auth_store)
        cell = gtk.CellRendererText()
        self.auth_combo.pack_start(cell, True)
        self.auth_combo.add_attribute(cell, 'text', 0)
        self.auth_combo.set_active(0)

        hbox = gtk.HBox()
        hbox.pack_start(gtk.Label(_("Authentication Type:")))
        hbox.pack_start(self.auth_combo)
        hbox.show_all()

        self.vbox.pack_start(hbox)

    def _key_combo_changed_cb(self, widget):
        self._update_response_sensitivity()

    def _get_security(self):
        key = self._entry.get_text()

        it = self.key_combo.get_active_iter()
        (key_type, ) = self.key_store.get(it, 1)

        if key_type == WEP_PASSPHRASE:
            key = hash_passphrase(key)
        elif key_type == WEP_ASCII:
            key = string_to_hex(key)

        it = self.auth_combo.get_active_iter()
        (auth_alg, ) = self.auth_store.get(it, 1)

        we_cipher = None
        if len(key) == 26:
            we_cipher = IW_AUTH_CIPHER_WEP104
        elif len(key) == 10:
            we_cipher = IW_AUTH_CIPHER_WEP40

        return (we_cipher, key, auth_alg)

    def print_security(self):
        (we_cipher, key, auth_alg) = self._get_security()
        print "Cipher: %d" % we_cipher
        print "Key: %s" % key
        print "Auth: %d" % auth_alg

    def create_security(self):
        (we_cipher, key, auth_alg) = self._get_security()
        return network.Security.new_from_args(we_cipher, (key, auth_alg))

    def _update_response_sensitivity(self, ignored=None):
        key = self._entry.get_text()
        it = self.key_combo.get_active_iter()
        (key_type, ) = self.key_store.get(it, 1)

        valid = False
        if key_type == WEP_PASSPHRASE:
            # As the md5 passphrase can be of any length and has no indicator,
            # we cannot check for the validity of the input.
            if len(key) > 0:
                valid = True
        elif key_type == WEP_ASCII:
            if len(key) == 5 or len(key) == 13:
                valid = string_is_ascii(key)
        elif key_type == WEP_HEX:
            if len(key) == 10 or len(key) == 26:
                valid = string_is_hex(key)

        self.set_response_sensitive(gtk.RESPONSE_OK, valid)

class WPAKeyDialog(KeyDialog):
    def __init__(self, net, async_cb, async_err_cb):
        KeyDialog.__init__(self, net, async_cb, async_err_cb)
        self.add_key_entry()

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

    def _get_security(self):
        ssid = self.get_network().get_ssid()
        key = self._entry.get_text()
        is_hex = string_is_hex(key)

        real_key = None
        if len(key) == 64 and is_hex:
            # Hex key
            real_key = key
        elif len(key) >= 8 and len(key) <= 63:
            # passphrase
            from subprocess import Popen, PIPE
            p = Popen(['/usr/sbin/wpa_passphrase', ssid, key], stdout=PIPE)
            for line in p.stdout:
                if line.strip().startswith("psk="):
                    real_key = line.strip()[4:]
            if p.wait() != 0:
                raise RuntimeError("Error hashing passphrase")
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

        return (we_cipher, real_key, wpa_ver)

    def print_security(self):
        (we_cipher, key, wpa_ver) = self._get_security()
        print "Cipher: %d" % we_cipher
        print "Key: %s" % key
        print "WPA Ver: %d" % wpa_ver

    def create_security(self):
        (we_cipher, key, wpa_ver) = self._get_security()
        return network.Security.new_from_args(
                        we_cipher, (key, wpa_ver, IW_AUTH_KEY_MGMT_PSK))

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
    if (caps & NM_802_11_CAP_CIPHER_TKIP or caps & NM_802_11_CAP_CIPHER_CCMP) \
            and (caps & NM_802_11_CAP_PROTO_WPA or \
                caps & NM_802_11_CAP_PROTO_WPA2):
        return WPAKeyDialog(net, async_cb, async_err_cb)
    elif (caps & NM_802_11_CAP_CIPHER_WEP40 or \
            caps & NM_802_11_CAP_CIPHER_WEP104) and \
            (caps & NM_802_11_CAP_PROTO_WEP):
        return WEPKeyDialog(net, async_cb, async_err_cb)
    else:
        raise RuntimeError("Unhandled network capabilities %x" % caps)
