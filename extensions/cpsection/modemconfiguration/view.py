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

from gettext import gettext as _
import logging

import gtk
import gobject

from sugar.graphics import style

from jarabe.controlpanel.sectionview import SectionView


APPLY_TIMEOUT = 1000


class EntryWithLabel(gtk.HBox):
    __gtype_name__ = 'SugarEntryWithLabel'

    def __init__(self, label_text):
        gtk.HBox.__init__(self, spacing=style.DEFAULT_SPACING)

        self.label = gtk.Label(label_text)
        self.label.modify_fg(gtk.STATE_NORMAL,
                        style.COLOR_SELECTION_GREY.get_gdk_color())
        self.label.set_alignment(1, 0.5)
        self.pack_start(self.label, expand=False)
        self.label.show()

        self._entry = gtk.Entry(25)
        self._entry.set_width_chars(25)
        self.pack_start(self._entry, expand=False)
        self._entry.show()

    def get_entry(self):
        return self._entry

    entry = gobject.property(type=object, getter=get_entry)


class ModemConfiguration(SectionView):
    def __init__(self, model, alerts=None):
        SectionView.__init__(self)

        self._model = model
        self.restart_alerts = alerts
        self._timeout_sid = 0

        self.set_border_width(style.DEFAULT_SPACING)
        self.set_spacing(style.DEFAULT_SPACING)
        self._group = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)

        explanation = _('You will need to provide the following information'
                        ' to set up a mobile broadband connection to a'
                        ' cellular (3G) network.')
        self._text = gtk.Label(explanation)
        self._text.set_width_chars(100)
        self._text.set_line_wrap(True)
        self._text.set_alignment(0, 0)
        self.pack_start(self._text, False)
        self._text.show()

        self._username_entry = EntryWithLabel(_('Username:'))
        self._username_entry.entry.connect('changed', self.__entry_changed_cb)
        self._group.add_widget(self._username_entry.label)
        self.pack_start(self._username_entry, expand=False)
        self._username_entry.show()

        self._password_entry = EntryWithLabel(_('Password:'))
        self._password_entry.entry.connect('changed', self.__entry_changed_cb)
        self._group.add_widget(self._password_entry.label)
        self.pack_start(self._password_entry, expand=False)
        self._password_entry.show()

        self._number_entry = EntryWithLabel(_('Number:'))
        self._number_entry.entry.connect('changed', self.__entry_changed_cb)
        self._group.add_widget(self._number_entry.label)
        self.pack_start(self._number_entry, expand=False)
        self._number_entry.show()

        self._apn_entry = EntryWithLabel(_('Access Point Name (APN):'))
        self._apn_entry.entry.connect('changed', self.__entry_changed_cb)
        self._group.add_widget(self._apn_entry.label)
        self.pack_start(self._apn_entry, expand=False)
        self._apn_entry.show()

        self._pin_entry = EntryWithLabel(_('Personal Identity Number (PIN):'))
        self._pin_entry.entry.connect('changed', self.__entry_changed_cb)
        self._group.add_widget(self._pin_entry.label)
        self.pack_start(self._pin_entry, expand=False)
        self._pin_entry.show()

        self.setup()

    def undo(self):
        self._model.undo()

    def _populate_entry(self, entrywithlabel, text):
        """Populate an entry with text, without triggering its 'changed'
        handler."""
        entry = entrywithlabel.entry
        entry.handler_block_by_func(self.__entry_changed_cb)
        entry.set_text(text)
        entry.handler_unblock_by_func(self.__entry_changed_cb)

    def setup(self):
        settings = self._model.get_modem_settings()
        self._populate_entry(self._username_entry,
            settings.get('username', ''))
        self._populate_entry(self._number_entry, settings.get('number', ''))
        self._populate_entry(self._apn_entry, settings.get('apn', ''))
        self._populate_entry(self._password_entry,
            settings.get('password', ''))
        self._populate_entry(self._pin_entry, settings.get('pin', ''))

    def __entry_changed_cb(self, widget, data=None):
        if self._timeout_sid:
            gobject.source_remove(self._timeout_sid)
        self._timeout_sid = gobject.timeout_add(APPLY_TIMEOUT,
                                                self.__timeout_cb)

    def __timeout_cb(self):
        self._timeout_sid = 0
        settings = {}
        settings['username'] = self._username_entry.entry.get_text()
        settings['password'] = self._password_entry.entry.get_text()
        settings['number'] = self._number_entry.entry.get_text()
        settings['apn'] = self._apn_entry.entry.get_text()
        settings['pin'] = self._pin_entry.entry.get_text()
        self._model.set_modem_settings(settings)
