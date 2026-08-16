# Copyright (C) 2006-2007 Red Hat, Inc.
# Copyright (C) 2009 One Laptop per Child
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import hashlib
from gettext import gettext as _

from gi.repository import Gtk


import dbus


from jarabe.model import network

IW_AUTH_ALG_OPEN_SYSTEM = 'open'
IW_AUTH_ALG_SHARED_KEY = 'shared'

WEP_PASSPHRASE = 1
WEP_HEX = 2
WEP_ASCII = 3


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
    # Use hexdigest() directly: digest() returns raw bytes that are not
    # guaranteed to be valid UTF-8, causing UnicodeDecodeError in Python 3.
    return hashlib.md5(passphrase.encode('utf-8')).hexdigest()[:26]


class CanceledKeyRequestError(dbus.DBusException):

    def __init__(self):
        dbus.DBusException.__init__(self)
        self._dbus_error_name = network.NM_SETTINGS_IFACE + '.CanceledError'


class KeyDialog(Gtk.Dialog):

    def __init__(self, ssid, flags, wpa_flags, rsn_flags, dev_caps, response):
        super().__init__()
        self.set_modal(True)
        self.set_title('Wireless Key Required')

        self._response = response
        self._entry = None
        self._ssid = ssid
        self._flags = flags
        self._wpa_flags = wpa_flags
        self._rsn_flags = rsn_flags
        self._dev_caps = dev_caps

        # Set spacing once for all children in the content area
        self.get_content_area().set_spacing(6)

        display_name = network.ssid_to_display_name(ssid)
        label = Gtk.Label(label=_("A wireless encryption key is required for\n"
                                  " the wireless network '%s'.")
                          % (display_name, ))
        label.set_hexpand(True)
        label.set_vexpand(True)
        self.get_content_area().append(label)
        label.set_visible(True)

        self.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        self.add_button(_("OK"), Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)

    def add_key_entry(self):
        self._entry = Gtk.Entry(visibility=True)
        self._entry.connect('changed', self._update_response_sensitivity)
        self._entry.connect('activate', self.__entry_activate_cb)
        self._entry.set_hexpand(True)
        self._entry.set_vexpand(True)
        self.get_content_area().append(self._entry)
        self._entry.set_visible(True)

        button = Gtk.CheckButton(label=_("Show Password"))
        button.set_active(self._entry.get_visibility())
        button.connect("toggled", self.__button_toggled_cb)
        button.set_hexpand(True)
        button.set_vexpand(True)
        self.get_content_area().append(button)
        button.set_visible(True)

        self._update_response_sensitivity()
        self._entry.grab_focus()

    def __entry_activate_cb(self, entry):
        self.response(Gtk.ResponseType.OK)

    def create_security(self):
        raise NotImplementedError

    def get_response_object(self):
        return self._response

    def __button_toggled_cb(self, button):
        self._entry.set_visibility(button.get_active())


class WEPKeyDialog(KeyDialog):

    def __init__(self, ssid, flags, wpa_flags, rsn_flags, dev_caps, response):
        KeyDialog.__init__(self, ssid, flags, wpa_flags, rsn_flags,
                           dev_caps, response)

        # WEP key type
        self.key_combo = Gtk.DropDown.new_from_strings([
            _('Passphrase (128-bit)'),
            _('Hex (40/128-bit)'),
            _('ASCII (40/128-bit)')
        ])
        self.key_combo.connect('notify::selected', self.__key_combo_changed_cb)
        self.key_combo.set_hexpand(True)
        self.key_combo.set_vexpand(True)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        label1 = Gtk.Label(label=_('Key Type:'))
        label1.set_hexpand(True)
        label1.set_vexpand(True)
        hbox.append(label1)
        label1.set_visible(True)
        
        hbox.append(self.key_combo)
        self.key_combo.set_visible(True)
        
        hbox.set_hexpand(True)
        hbox.set_vexpand(True)
        self.get_content_area().append(hbox)
        hbox.set_visible(True)

        # Key entry field
        self.add_key_entry()

        # WEP authentication mode
        self.auth_combo = Gtk.DropDown.new_from_strings([
            _('Open System'),
            _('Shared Key')
        ])
        self.auth_combo.set_hexpand(True)
        self.auth_combo.set_vexpand(True)

        hbox2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        label2 = Gtk.Label(label=_('Authentication Type:'))
        label2.set_hexpand(True)
        label2.set_vexpand(True)
        hbox2.append(label2)
        label2.set_visible(True)
        
        hbox2.append(self.auth_combo)
        self.auth_combo.set_visible(True)
        
        hbox2.set_hexpand(True)
        hbox2.set_vexpand(True)
        self.get_content_area().append(hbox2)
        hbox2.set_visible(True)

    def __key_combo_changed_cb(self, widget, pspec):
        self._update_response_sensitivity()

    def _get_security(self):
        key = self._entry.get_text()

        selected_key = self.key_combo.get_selected()
        if selected_key == 0:
            key_type = WEP_PASSPHRASE
        elif selected_key == 1:
            key_type = WEP_HEX
        else:
            key_type = WEP_ASCII

        if key_type == WEP_PASSPHRASE:
            key = hash_passphrase(key)
        elif key_type == WEP_ASCII:
            key = string_to_hex(key)

        selected_auth = self.auth_combo.get_selected()
        auth_alg = IW_AUTH_ALG_OPEN_SYSTEM if selected_auth == 0 else IW_AUTH_ALG_SHARED_KEY

        return (key, auth_alg)

    def print_security(self):
        (key, auth_alg) = self._get_security()
        print('Key: %s' % key)
        print('Auth: %s' % auth_alg)

    def create_security(self):
        (key, auth_alg) = self._get_security()
        wsec = {'wep-key0': key, 'auth-alg': auth_alg}
        return {'802-11-wireless-security': wsec}

    def _update_response_sensitivity(self, ignored=None):
        key = self._entry.get_text()
        
        selected_key = self.key_combo.get_selected()
        if selected_key == 0:
            key_type = WEP_PASSPHRASE
        elif selected_key == 1:
            key_type = WEP_HEX
        else:
            key_type = WEP_ASCII

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

        self.set_response_sensitive(Gtk.ResponseType.OK, valid)


class WPAKeyDialog(KeyDialog):

    def __init__(self, ssid, flags, wpa_flags, rsn_flags, dev_caps, response):
        KeyDialog.__init__(self, ssid, flags, wpa_flags, rsn_flags,
                           dev_caps, response)
        self.add_key_entry()

        self.combo = Gtk.DropDown.new_from_strings([_('WPA & WPA2 Personal')])
        self.combo.set_hexpand(True)
        self.combo.set_vexpand(True)

        self.hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        label = Gtk.Label(label=_('Wireless Security:'))
        label.set_hexpand(True)
        label.set_vexpand(True)
        self.hbox.append(label)
        label.set_visible(True)
        
        self.hbox.append(self.combo)
        self.combo.set_visible(True)
        
        self.hbox.set_hexpand(True)
        self.hbox.set_vexpand(True)
        self.get_content_area().append(self.hbox)
        self.hbox.set_visible(True)

    def _get_security(self):
        return self._entry.get_text()

    def print_security(self):
        key = self._get_security()
        print('Key: %s' % key)

    def create_security(self):
        wsec = {'psk': self._get_security()}
        return {'802-11-wireless-security': wsec}

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
        self.set_response_sensitive(Gtk.ResponseType.OK, valid)
        return False


def create(ssid, flags, wpa_flags, rsn_flags, dev_caps, response):
    if wpa_flags == network.NM_802_11_AP_SEC_NONE and \
            rsn_flags == network.NM_802_11_AP_SEC_NONE:
        key_dialog = WEPKeyDialog(ssid, flags, wpa_flags, rsn_flags,
                                  dev_caps, response)
    else:
        key_dialog = WPAKeyDialog(ssid, flags, wpa_flags, rsn_flags,
                                  dev_caps, response)

    key_dialog.connect('response', _key_dialog_response_cb)
    key_dialog.set_visible(True)


def _key_dialog_response_cb(key_dialog, response_id):
    response = key_dialog.get_response_object()
    secrets = None
    if response_id == Gtk.ResponseType.OK:
        secrets = key_dialog.create_security()

    if response_id in [Gtk.ResponseType.CANCEL, Gtk.ResponseType.NONE,
                       Gtk.ResponseType.CLOSE, Gtk.ResponseType.DELETE_EVENT]:
        # key dialog was canceled; send the error back to NM
        response.set_error(CanceledKeyRequestError())
    elif response_id == Gtk.ResponseType.OK:
        if not secrets:
            raise RuntimeError('Invalid security arguments.')
        response.set_secrets(secrets)
    else:
        raise RuntimeError('Unhandled key dialog response %d' % response_id)

    key_dialog.close()
