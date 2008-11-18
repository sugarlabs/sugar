# Copyright (C) 2008, OLPC
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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

import gtk
import gobject
import gettext

from sugar.graphics import style
from sugar.graphics.icon import Icon

from jarabe.controlpanel.sectionview import SectionView
from jarabe.controlpanel.inlinealert import InlineAlert

_translate_language = lambda msg: gettext.dgettext('iso_639', msg) 
_translate_country = lambda msg: gettext.dgettext('iso_3166', msg)

CLASS = 'Language'
ICON = 'module-language'
TITLE = gettext.gettext('Language')

class Language(SectionView):
    def __init__(self, model, alerts):
        SectionView.__init__(self)

        self._model = model
        self.restart_alerts = alerts
        self._lang_sid = 0
        self._selected_lang_count = 0
        self._labels = []
        self._stores = []
        self._comboboxes = []
        self._add_remove_boxes = []
        self._changed = False
        self._cursor_change_handler = None

        self._available_locales = self._model.read_all_languages()
        self._selected_locales = self._model.get_languages()

        self.set_border_width(style.DEFAULT_SPACING * 2)
        self.set_spacing(style.DEFAULT_SPACING)

        self._table = gtk.Table(rows=1, columns=3, homogeneous=False)
        self.pack_start(self._table, False)
        self._table.show()

        self._lang_alert_box = gtk.HBox(spacing=style.DEFAULT_SPACING)
        self.pack_start(self._lang_alert_box, False)

        self._lang_alert = InlineAlert()        
        self._lang_alert_box.pack_start(self._lang_alert)
        if 'lang' in self.restart_alerts:
            self._lang_alert.props.msg = self.restart_msg
            self._lang_alert.show()
        self._lang_alert_box.show()

        self.setup()

    def _add_row(self, locale_code=None):
        '''Adds a row to the table'''

        self._selected_lang_count += 1
        
        self._table.resize(self._selected_lang_count, 3)

        label = gtk.Label(str=str(self._selected_lang_count))
        self._labels.append(label)
        self._attach_to_table(label, 0, 1, padding=1)
        label.show()
        
                
        store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        for language, country, code in self._available_locales:
            description = '%s (%s)' % (_translate_language(language), \
                _translate_country(country))
            store.append([code, description])

        combobox = gtk.ComboBox(model=store)
        cell = gtk.CellRendererText()
        combobox.pack_start(cell)
        combobox.add_attribute(cell, 'text', 1)

        if locale_code:
            for row in store:
                lang = locale_code.split('.')[0]
                lang_column = row[0].split('.')[0]
                if lang in lang_column: 
                    combobox.set_active_iter(row.iter)
                    break
        else:
            combobox.set_active(1)

        combobox.connect('changed', self.__combobox_changed_cb)

        self._stores.append(store)
        self._comboboxes.append(combobox)
        self._attach_to_table(combobox, 1, 2, yoptions=gtk.SHRINK)

        add_remove_box = self._create_add_remove_box()
        self._add_remove_boxes.append(add_remove_box)
        self._attach_to_table(add_remove_box, 2, 3)

        add_remove_box.show_all()
        
        if self._selected_lang_count > 1:
            previous_add_removes = self._add_remove_boxes[-2]
            previous_add_removes.hide_all()

        combobox.show()

    def _attach_to_table(self, widget, row, column, padding=20, \
            yoptions=gtk.FILL):
        self._table.attach(widget, row, column, \
            self._selected_lang_count - 1, self._selected_lang_count, \
            xoptions=gtk.FILL, yoptions=yoptions, xpadding=padding, \
                ypadding=padding)

    def _delete_last_row(self):
        '''Deletes the last row of the table'''

        self._selected_lang_count -= 1

        label, add_remove_box, combobox, store = self._get_last_row()
        
        label.destroy()
        add_remove_box.destroy()
        combobox.destroy()
        del(store)

        self._table.resize(self._selected_lang_count, 3)

        self._add_remove_boxes[-1].show_all()

    def _get_last_row(self):
        label = self._labels.pop()
        add_remove_box = self._add_remove_boxes.pop()
        combobox = self._comboboxes.pop()
        store = self._stores.pop()

        return label, add_remove_box, combobox, store

    def setup(self):
        for locale in self._selected_locales:
            self._add_row(locale_code=locale)

    def undo(self):
        self._model.undo()
        self._lang_alert.hide()

    def _create_add_remove_box(self):
        '''Creates gtk.Hbox with add/remove buttons'''
        add_icon =  Icon(icon_name='list-add')

        add_button = gtk.Button()
        add_button.set_image(add_icon)
        add_button.connect('clicked',
                            self.__add_button_clicked_cb)

        remove_icon =  Icon(icon_name='list-remove')
        remove_button = gtk.Button()
        remove_button.set_image(remove_icon)
        remove_button.connect('clicked',
                            self.__remove_button_clicked_cb)

        if self._selected_lang_count == 1:
            remove_button.set_sensitive(False)

        add_remove_box = gtk.HButtonBox()
        add_remove_box.set_layout(gtk.BUTTONBOX_START)
        add_remove_box.set_spacing(10)
        add_remove_box.pack_start(add_button)
        add_remove_box.pack_start(remove_button)

        return add_remove_box

    def __add_button_clicked_cb(self, button):
        self._add_row()
        self._check_change()

    def __remove_button_clicked_cb(self, button):
        self._delete_last_row()
        self._check_change()

    def __combobox_changed_cb(self, button):
        self._check_change()

    def _check_change(self):
        selected_langs = self._get_selected_langs()
        self._changed = (selected_langs != self._selected_locales)

        if self._changed == False:
            # The user reverted back to the original config
            self.needs_restart = False
            if 'lang' in self.restart_alerts:
                self.restart_alerts.remove('lang')
            self._lang_alert.hide()
            if self._lang_sid:
                gobject.source_remove(self._lang_sid)
            self._model.undo()
            return False

        if self._lang_sid:
            gobject.source_remove(self._lang_sid)
        self._lang_sid = gobject.timeout_add(self._APPLY_TIMEOUT,
                                            self.__lang_timeout_cb,
                                            selected_langs)

    def _get_selected_langs(self):
        new_codes = []
        for combobox in self._comboboxes:
            iter = combobox.get_active_iter()
            model = combobox.get_model()
            lang_code = model.get(iter, 0)[0]
            new_codes.append(lang_code)
        
        return new_codes

    def __lang_timeout_cb(self, codes):
        self._lang_sid = 0
        self._model.set_languages(codes)
        self.restart_alerts.append('lang')
        self.needs_restart = True
        self._lang_alert.props.msg = self.restart_msg
        self._lang_alert.show()
        return False
