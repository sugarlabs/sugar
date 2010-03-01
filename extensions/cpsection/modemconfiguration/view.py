# Copyright (C) 2009 Paraguay Educa, Martin Abente
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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  US

import os
import logging
from gettext import gettext as _

import gtk
import gobject

from sugar.graphics import style

from jarabe.controlpanel.sectionview import SectionView

APPLY_TIMEOUT = 1000

class EntryWithLabel(gtk.HBox):
    __gtype_name__ = "SugarEntryWithLabel"

    def __init__(self, label_text):
        gtk.HBox.__init__(self, spacing=style.DEFAULT_SPACING)

        self._timeout_sid = 0
        self._changed_handler = None
        self._is_valid = True

        self.label = gtk.Label(label_text)
        self.label.modify_fg(gtk.STATE_NORMAL,
                        style.COLOR_SELECTION_GREY.get_gdk_color())
        self.label.set_alignment(1, 0.5)
        self.pack_start(self.label, expand=False)
        self.label.show()

        self._entry = gtk.Entry(25)
        self._entry.connect('changed', self.__entry_changed_cb)
        self._entry.set_width_chars(25)
        self.pack_start(self._entry, expand=False)
        self._entry.show()

    def __entry_changed_cb(self, widget, data=None):
        if self._timeout_sid:
            gobject.source_remove(self._timeout_sid)
        self._timeout_sid = gobject.timeout_add(APPLY_TIMEOUT, 
                                                self.__timeout_cb)

    def __timeout_cb(self):
        self._timeout_sid = 0

        if self._entry.get_text() == self.get_value():
            return False

        try:
            self.set_value(self._entry.get_text()) 
        except ValueError:
            self._is_valid = False
        else:
            self._is_valid = True

        self.notify('is-valid')

        return False

    def set_text_from_model(self):
        self._entry.set_text(self.get_value()) 

    def get_value(self):
        raise NotImplementedError

    def set_value(self):
        raise NotImplementedError    

    def _get_is_valid(self):
        return self._is_valid
    is_valid = gobject.property(type=bool, getter=_get_is_valid, default=True)

class UsernameEntry(EntryWithLabel):
    def __init__(self, model):
        EntryWithLabel.__init__(self, _('Username:'))
        self._model = model

    def get_value(self):
        return self._model.get_username()

    def set_value(self, username):
        self._model.set_username(username)

class PasswordEntry(EntryWithLabel):
    def __init__(self, model):
        EntryWithLabel.__init__(self, _('Password:'))
        self._model = model

    def get_value(self):
        return self._model.get_password()

    def set_value(self, password):
        self._model.set_password(password)

class NumberEntry(EntryWithLabel):
    def __init__(self, model):
        EntryWithLabel.__init__(self, _('Number:'))
        self._model = model

    def get_value(self):
        return self._model.get_number()

    def set_value(self, number):
        self._model.set_number(number)

class ApnEntry(EntryWithLabel):
    def __init__(self, model):
        EntryWithLabel.__init__(self, _('Access Point Name (APN):'))
        self._model = model

    def get_value(self):
        return self._model.get_apn()

    def set_value(self, apn):
        self._model.set_apn(apn)

class PinEntry(EntryWithLabel):
    def __init__(self, model):
        EntryWithLabel.__init__(self, _('Personal Identity Number (PIN):'))
        self._model = model

    def get_value(self):
        return self._model.get_pin()

    def set_value(self, pin):
        self._model.set_pin(pin)

class PukEntry(EntryWithLabel):
    def __init__(self, model):
        EntryWithLabel.__init__(self, _('Personal Unblocking Key (PUK):'))
        self._model = model

    def get_value(self):
        return self._model.get_puk()

    def set_value(self, puk):
        self._model.set_puk(puk)


class ModemConfiguration(SectionView):
    def __init__(self, model, alerts=None):
        SectionView.__init__(self)

        self._model = model
        self.restart_alerts = alerts

        self.set_border_width(style.DEFAULT_SPACING)
        self.set_spacing(style.DEFAULT_SPACING)
        self._group = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)

        explanation = _("You will need to provide the following " \
                            "information to set up a mobile " \
                            "broadband connection to a cellular "\
                            "(3G) network.")
        self._text = gtk.Label(explanation)
        self._text.set_width_chars(100)
        self._text.set_line_wrap(True)
        self._text.set_alignment(0, 0)
        self.pack_start(self._text, False)
        self._text.show()

        self._username_entry = UsernameEntry(model)
        self._username_entry.connect('notify::is-valid',
                                     self.__notify_is_valid_cb)
        self._group.add_widget(self._username_entry.label)
        self.pack_start(self._username_entry, expand=False)
        self._username_entry.show()

        self._password_entry = PasswordEntry(model)
        self._password_entry.connect('notify::is-valid',
                                     self.__notify_is_valid_cb)
        self._group.add_widget(self._password_entry.label)
        self.pack_start(self._password_entry, expand=False)
        self._password_entry.show()

        self._number_entry = NumberEntry(model)
        self._number_entry.connect('notify::is-valid',
                                   self.__notify_is_valid_cb)
        self._group.add_widget(self._number_entry.label)
        self.pack_start(self._number_entry, expand=False)
        self._number_entry.show()

        self._apn_entry = ApnEntry(model)
        self._apn_entry.connect('notify::is-valid',
                                self.__notify_is_valid_cb)
        self._group.add_widget(self._apn_entry.label)
        self.pack_start(self._apn_entry, expand=False)
        self._apn_entry.show()

        self._pin_entry = PinEntry(model)
        self._pin_entry.connect('notify::is-valid',
                                self.__notify_is_valid_cb)
        self._group.add_widget(self._pin_entry.label)
        self.pack_start(self._pin_entry, expand=False)
        self._pin_entry.show()
        
        self._puk_entry = PukEntry(model)
        self._puk_entry.connect('notify::is-valid',
                                self.__notify_is_valid_cb)
        self._group.add_widget(self._puk_entry.label)
        self.pack_start(self._puk_entry, expand=False)        
        self._puk_entry.show()

        self.setup()

    def setup(self):
        self._username_entry.set_text_from_model()
        self._password_entry.set_text_from_model()
        self._number_entry.set_text_from_model()
        self._apn_entry.set_text_from_model()
        self._pin_entry.set_text_from_model()
        self._puk_entry.set_text_from_model()

        self.needs_restart = False

    def undo(self):
        self._model.undo()

    def _validate(self):
        if self._username_entry.is_valid and \
            self._password_entry.is_valid and \
                self._number_entry.is_valid and \
                    self._apn_entry.is_valid and \
                        self._pin_entry.is_valid and \
                            self._puk_entry.is_valid:
                                self.props.is_valid = True
        else:
            self.props.is_valid = False

    def __notify_is_valid_cb(self, entry, pspec):
        if entry.is_valid:
            self.needs_restart = True
        self._validate()

