# Copyright (C) 2013, Sugar Labs
# Copyright (C) 2009, OLPC
# Author: Sayamindu Dasgupta <sayamindu@laptop.org>
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


import os
import locale

from gi.repository import Gtk
from gi.repository import GdkX11
from gi.repository import GObject
from gi.repository import Pango

import logging
from gettext import gettext as _

from sugar3.graphics import style
from sugar3.graphics.icon import Icon

from jarabe.controlpanel.sectionview import SectionView
from jarabe.config import data_path

CLASS = 'Language'
ICON = 'module-keyboard'
TITLE = _('Keyboard')

_APPLY_TIMEOUT = 500

_iso_639_1_to_2 = {}

# TODO: This cpsection adds checks for xklavier in bin/sugar-session and
#      src/jarabe/controlpanel/gui.py. We should get rid of these checks
#      once python-xklavier has been packaged for all major distributions
#      For more information, see: http://dev.sugarlabs.org/ticket/407


def _build_ISO_639_dictionary():
    """ The keyboard section of the control panel requires a conversion
    between ISO 639 two-character codes and three-character code. This
    method uses the table available at:
    http://www.loc.gov/standards/iso639-2/ISO-639-2_utf-8.txt
    """

    ISO_DATA_FILE = 'ISO-639-2_utf-8.txt'

    path = os.path.join(data_path, ISO_DATA_FILE)
    if os.path.exists(path):
        f = open(path, 'r')
        for line in f:
            codes = line.split('|')
            if codes[2] != '':
                _iso_639_1_to_2[codes[2]] = codes[0]
    else:
        logging.error('%s not found' % (ISO_DATA_FILE))


class LayoutCombo(Gtk.HBox):
    """
    Custom GTK widget with two comboboxes side by side, one for layout, and
    the other for variants for the selected layout.
    """

    __gsignals__ = {
        'selection-changed': (GObject.SignalFlags.RUN_LAST, None,
                              (GObject.TYPE_STRING, GObject.TYPE_INT)),
    }

    def __init__(self, keyboard_manager, n):
        GObject.GObject.__init__(self)
        self._keyboard_manager = keyboard_manager
        self._index = n

        self.set_border_width(style.DEFAULT_SPACING)
        self.set_spacing(style.DEFAULT_SPACING)

        label = Gtk.Label(label=' <b>%s</b> ' % str(n + 1))
        label.set_use_markup(True)
        label.modify_fg(Gtk.StateType.NORMAL,
                        style.COLOR_SELECTION_GREY.get_gdk_color())
        label.set_alignment(0.5, 0.5)
        self.pack_start(label, False, True, 0)

        self._klang_store = Gtk.ListStore(GObject.TYPE_STRING,
                                          GObject.TYPE_STRING)
        for description, name in self._keyboard_manager.get_languages():
            self._klang_store.append([name, description])

        self._klang_combo = Gtk.ComboBox(model=self._klang_store)
        self._klang_combo_changed_id = \
            self._klang_combo.connect('changed', self._klang_combo_changed_cb)
        cell = Gtk.CellRendererText()
        cell.props.ellipsize = Pango.EllipsizeMode.MIDDLE
        cell.props.ellipsize_set = True
        self._klang_combo.pack_start(cell, True)
        self._klang_combo.add_attribute(cell, 'text', 1)
        self.pack_start(self._klang_combo, expand=True, fill=True, padding=0)

        self._kvariant_store = None
        self._kvariant_combo = Gtk.ComboBox(model=None)
        self._kvariant_combo_changed_id = \
            self._kvariant_combo.connect('changed',
                                         self._kvariant_combo_changed_cb)
        cell = Gtk.CellRendererText()
        cell.props.ellipsize = Pango.EllipsizeMode.MIDDLE
        cell.props.ellipsize_set = True
        self._kvariant_combo.pack_start(cell, True)
        self._kvariant_combo.add_attribute(cell, 'text', 1)
        self.pack_start(self._kvariant_combo, expand=True, fill=True,
                        padding=0)

        self._klang_combo.set_active(self._index)

    def select_layout(self, layout):
        """Select a given keyboard layout and show appropriate variants"""

        self._kvariant_combo.handler_block(self._kvariant_combo_changed_id)

        # Look for $LANG first
        for lang in os.environ.get('LANG',
                                   locale.getdefaultlocale()[0]).split(':'):
            if lang[0:2] in _iso_639_1_to_2:
                if self._look_for_lang_and_layout(_iso_639_1_to_2[lang[0:2]],
                                                  layout):
                    return True

        # Then look for any language
        if self._look_for_lang_and_layout(None, layout):
            return True

        # Finally, select a default
        self._kvariant_combo.handler_unblock(self._kvariant_combo_changed_id)
        self._klang_combo.set_active(0)
        return False

    def _look_for_lang_and_layout(self, lang, layout):
        for i in range(0, len(self._klang_store)):
            if lang == self._klang_store[i][0] or lang is None:
                self._klang_combo.set_active(i)
                for j in range(0, len(self._kvariant_store)):
                    if self._kvariant_store[j][0] == layout:
                        self._kvariant_combo.set_active(j)
                        self._kvariant_combo.handler_unblock(
                            self._kvariant_combo_changed_id)
                        return True
        return False

    def get_layout(self):
        """Gets the selected layout (with variant)"""
        it = self._kvariant_combo.get_active_iter()
        model = self._kvariant_combo.get_model()
        return model.get(it, 0)[0]

    def _set_kvariant_store(self, lang):
        self._kvariant_store = Gtk.ListStore(GObject.TYPE_STRING,
                                             GObject.TYPE_STRING)
        layouts = self._keyboard_manager.get_layouts_for_language(lang)
        for description, name in layouts:
            self._kvariant_store.append([name, description])
        self._kvariant_combo.set_model(self._kvariant_store)
        self._kvariant_combo.set_active(0)

    def _klang_combo_changed_cb(self, combobox):
        it = combobox.get_active_iter()
        model = combobox.get_model()
        lang = model.get(it, 0)[0]
        self._set_kvariant_store(lang)

    def _kvariant_combo_changed_cb(self, combobox):
        it = combobox.get_active_iter()
        model = combobox.get_model()
        layout = model.get(it, 0)[0]
        self.emit('selection-changed', layout, self._index)


class Keyboard(SectionView):
    def __init__(self, model, alerts):
        SectionView.__init__(self)

        self._model = model

        self._kmodel = None
        self._selected_kmodel = None

        self._klayouts = []
        self._selected_klayouts = []

        self._group_switch_option = None
        self._selected_group_switch_option = None

        self.set_border_width(style.DEFAULT_SPACING * 2)
        self.set_spacing(style.DEFAULT_SPACING)

        self._layout_table = Gtk.Table(rows=4, columns=2, homogeneous=False)

        _build_ISO_639_dictionary()

        self._keyboard_manager = model.KeyboardManager(
            GdkX11.x11_get_default_xdisplay())

        self._layout_combo_list = []
        self._layout_addremovebox_list = []

        scrollwindow = Gtk.ScrolledWindow()
        scrollwindow.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.pack_start(scrollwindow, True, True, 0)
        scrollwindow.show()

        self._vbox = Gtk.VBox()
        scrollwindow.add_with_viewport(self._vbox)

        self.__kmodel_sid = None
        self.__layout_sid = None
        self.__group_switch_sid = None

        self._setup_kmodel()
        self._setup_layouts()
        self._setup_group_switch_option()

        self._vbox.show()

    def _setup_kmodel(self):
        """Adds the controls for changing the keyboard model"""
        separator_kmodel = Gtk.HSeparator()
        self._vbox.pack_start(separator_kmodel, False, True, 0)
        separator_kmodel.show_all()

        label_kmodel = Gtk.Label(label=_('Keyboard Model'))
        label_kmodel.set_alignment(0, 0)
        self._vbox.pack_start(label_kmodel, False, True, 0)
        label_kmodel.show_all()

        box_kmodel = Gtk.VBox()
        box_kmodel.set_border_width(style.DEFAULT_SPACING * 2)
        box_kmodel.set_spacing(style.DEFAULT_SPACING)

        kmodel_store = Gtk.ListStore(GObject.TYPE_STRING,
                                     GObject.TYPE_STRING)
        for description, name in self._keyboard_manager.get_models():
            kmodel_store.append([name, description])

        kmodel_combo = Gtk.ComboBox(model=kmodel_store)
        cell = Gtk.CellRendererText()
        cell.props.ellipsize = Pango.EllipsizeMode.MIDDLE
        cell.props.ellipsize_set = True
        kmodel_combo.pack_start(cell, True)
        kmodel_combo.add_attribute(cell, 'text', 1)

        self._kmodel = self._keyboard_manager.get_current_model()
        if self._kmodel is not None:
            for row in kmodel_store:
                if self._kmodel in row[0]:
                    kmodel_combo.set_active_iter(row.iter)
                    break

        box_kmodel.pack_start(kmodel_combo, False, True, 0)
        self._vbox.pack_start(box_kmodel, False, True, 0)
        box_kmodel.show_all()

        kmodel_combo.connect('changed', self.__kmodel_changed_cb)

    def __kmodel_changed_cb(self, combobox):
        if self.__kmodel_sid is not None:
            GObject.source_remove(self.__kmodel_sid)
        self.__kmodel_sid = GObject.timeout_add(_APPLY_TIMEOUT,
                                                self.__kmodel_timeout_cb,
                                                combobox)

    def __kmodel_timeout_cb(self, combobox):
        it = combobox.get_active_iter()
        model = combobox.get_model()
        self._selected_kmodel = model.get(it, 0)[0]
        if self._selected_kmodel == self._keyboard_manager.get_current_model():
            return
        try:
            self._keyboard_manager.set_model(self._selected_kmodel)
        except Exception:
            logging.exception('Could not set new keyboard model')

        return False

    def _setup_group_switch_option(self):
        """Adds the controls for changing the group switch option of keyboard
        """
        separator_group_option = Gtk.HSeparator()
        self._vbox.pack_start(separator_group_option, False, True, 0)
        separator_group_option.show_all()

        label_group_option = Gtk.Label(label=_('Key(s) to change layout'))
        label_group_option.set_alignment(0, 0)
        self._vbox.pack_start(label_group_option, False, True, 0)
        label_group_option.show_all()

        box_group_option = Gtk.VBox()
        box_group_option.set_border_width(style.DEFAULT_SPACING * 2)
        box_group_option.set_spacing(style.DEFAULT_SPACING)

        group_option_store = Gtk.ListStore(GObject.TYPE_STRING,
                                           GObject.TYPE_STRING)
        for description, name in self._keyboard_manager.get_options_group():
            group_option_store.append([name, description])

        group_option_combo = Gtk.ComboBox(model=group_option_store)
        cell = Gtk.CellRendererText()
        cell.props.ellipsize = Pango.EllipsizeMode.MIDDLE
        cell.props.ellipsize_set = True
        group_option_combo.pack_start(cell, True)
        group_option_combo.add_attribute(cell, 'text', 1)

        self._group_switch_option = \
            self._keyboard_manager.get_current_option_group()
        if not self._group_switch_option:
            group_option_combo.set_active(0)
        else:
            found = False
            for row in group_option_store:
                if self._group_switch_option in row[0]:
                    group_option_combo.set_active_iter(row.iter)
                    found = True
                    break
            if not found:
                group_option_combo.set_active(0)

        box_group_option.pack_start(group_option_combo, False, True, 0)
        self._vbox.pack_start(box_group_option, False, True, 0)
        box_group_option.show_all()

        group_option_combo.connect('changed', self.__group_switch_changed_cb)

    def __group_switch_changed_cb(self, combobox):
        if self.__group_switch_sid is not None:
            GObject.source_remove(self.__group_switch_sid)
        self.__group_switch_sid = GObject.timeout_add(
            _APPLY_TIMEOUT, self.__group_switch_timeout_cb, combobox)

    def __group_switch_timeout_cb(self, combobox):
        it = combobox.get_active_iter()
        model = combobox.get_model()
        self._selected_group_switch_option = model.get(it, 0)[0]
        if self._selected_group_switch_option == \
                self._keyboard_manager.get_current_option_group():
            return
        try:
            self._keyboard_manager.set_option_group(
                self._selected_group_switch_option)
        except Exception:
            logging.exception('Could not set new keyboard group switch option')

        return False

    def _setup_layouts(self):
        """Adds the controls for changing the keyboard layouts"""
        separator_klayout = Gtk.HSeparator()
        self._vbox.pack_start(separator_klayout, False, True, 0)
        separator_klayout.show_all()

        label_klayout = Gtk.Label(label=_('Keyboard Layout(s)'))
        label_klayout.set_alignment(0, 0)
        label_klayout.show_all()
        self._vbox.pack_start(label_klayout, False, True, 0)

        self._klayouts = self._keyboard_manager.get_current_layouts()
        for i in range(0, self._keyboard_manager.get_max_layouts()):
            add_remove_box = self.__create_add_remove_box()
            self._layout_addremovebox_list.append(add_remove_box)
            self._layout_table.attach(add_remove_box, 1, 2, i, i + 1)

            layout_combo = LayoutCombo(self._keyboard_manager, i)
            layout_combo.connect('selection-changed',
                                 self.__layout_combo_selection_changed_cb)
            self._layout_combo_list.append(layout_combo)
            self._layout_table.attach(layout_combo, 0, 1, i, i + 1)

            if i < len(self._klayouts):
                layout_combo.show_all()
                layout_combo.select_layout(self._klayouts[i])

        self._vbox.pack_start(self._layout_table, False, True, 0)
        self._layout_table.set_size_request(
            self._vbox.get_size_request()[0], -1)
        self._layout_table.show()
        self._update_klayouts()

    def __determine_add_remove_box_visibility(self):
        i = 1
        for box in self._layout_addremovebox_list:
            if not i == len(self._selected_klayouts):
                box.props.visible = False
            else:
                box.show_all()
                if i == 1:
                    # First row - no need for showing remove btn
                    add, remove = box.get_children()
                    remove.props.visible = False
                if i == self._keyboard_manager.get_max_layouts():
                    # Last row - no need for showing add btn
                    add, remove = box.get_children()
                    add.props.visible = False
            i += 1

    def __create_add_remove_box(self):
        """Creates Gtk.Hbox with add/remove buttons"""
        add_icon = Icon(icon_name='list-add')

        add_button = Gtk.Button()
        add_button.set_image(add_icon)
        add_button.connect('clicked',
                           self.__add_button_clicked_cb)

        remove_icon = Icon(icon_name='list-remove')
        remove_button = Gtk.Button()
        remove_button.set_image(remove_icon)
        remove_button.connect('clicked',
                              self.__remove_button_clicked_cb)

        add_remove_box = Gtk.HButtonBox()
        add_remove_box.set_layout(Gtk.ButtonBoxStyle.START)
        add_remove_box.set_spacing(10)
        add_remove_box.pack_start(add_button, True, True, 0)
        add_remove_box.pack_start(remove_button, True, True, 0)

        return add_remove_box

    def __layout_combo_selection_changed_cb(self, combo, layout, index):
        self._update_klayouts()

    def __add_button_clicked_cb(self, button):
        self._layout_combo_list[len(self._selected_klayouts)].show_all()
        self._update_klayouts()

    def __remove_button_clicked_cb(self, button):
        self._layout_combo_list[len(self._selected_klayouts) - 1].hide()
        self._update_klayouts()

    def _update_klayouts(self):
        """Responds to any changes in the keyboard layout options"""
        self._selected_klayouts = []
        for combo in self._layout_combo_list:
            if combo.props.visible:
                self._selected_klayouts.append(combo.get_layout())

        self.__determine_add_remove_box_visibility()

        if self.__layout_sid is not None:
            GObject.source_remove(self.__layout_sid)
        self.__layout_sid = GObject.timeout_add(_APPLY_TIMEOUT,
                                                self.__layout_timeout_cb)

    def __layout_timeout_cb(self):
        if self._selected_klayouts == \
                self._keyboard_manager.get_current_layouts():
            return
        try:
            self._keyboard_manager.set_layouts(self._selected_klayouts)
        except Exception:
            logging.exception('Could not set new keyboard layouts')

        return False

    def undo(self):
        """Reverts back to the original keyboard configuration"""
        self._keyboard_manager.set_model(self._kmodel)
        self._keyboard_manager.set_layouts(self._klayouts)
        self._keyboard_manager.set_option_group(self._group_switch_option)
