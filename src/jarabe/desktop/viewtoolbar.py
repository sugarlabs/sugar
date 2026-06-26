# Copyright (C) 2006-2007 Red Hat, Inc.
# Copyright (C) 2009 Tomeu Vizoso, Simon Schampijer
# Copyright (C) 2009-2012 One Laptop per Child
# Copyright (C) 2010 Collabora Ltd. <http://www.collabora.co.uk/>
# Copyright (C) 2008-2013 Sugar Labs
# Copyright (C) 2013 Daniel Francis
# Copyright (C) 2013 Walter Bender
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

from gettext import gettext as _
import logging

from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import GLib

from sugar4.graphics import style
from sugar4.graphics import iconentry
from sugar4.graphics.radiotoolbutton import RadioToolButton



from jarabe.desktop import favoritesview
from jarabe.model import desktop

_AUTOSEARCH_TIMEOUT = 1000

# Gtk.Box + regular buttons would require toolkit changes too.


class ViewToolbar(Gtk.Box):
    __gtype_name__ = 'SugarViewToolbar'

    __gsignals__ = {
        'query-changed': (GObject.SignalFlags.RUN_FIRST, None,
                          ([str])),
        'view-changed': (GObject.SignalFlags.RUN_FIRST, None,
                         ([object])),
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.add_css_class('sugar-toolbar')

        self._favorites_views_indicies = []
        for i in range(desktop.get_number_of_views()):
            self._favorites_views_indicies.append(i)
        self._list_view_index = self._favorites_views_indicies[-1] + 1

        self._desktop_model = desktop.get_model()
        self._desktop_model.connect('desktop-view-icons-changed',
                                    self.__desktop_view_icons_changed_cb)

        self._query = None
        self._autosearch_timer = None

        self._add_separator()

        self.search_entry = iconentry.IconEntry()
        self.search_entry.set_icon_from_name(iconentry.ICON_ENTRY_PRIMARY,
                                             'entry-search')
        self.set_placeholder_text_for_view(_('Home'))
        self.search_entry.add_clear_button()
        self.search_entry.set_width_chars(25)
        self.search_entry.connect('activate', self._entry_activated_cb)
        self.search_entry.connect('changed', self._entry_changed_cb)
        
        self.append(self.search_entry)
        self.search_entry.set_visible(True)

        self._add_separator(expand=True)

        self._button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._favorites_buttons = []
        for i in range(desktop.get_number_of_views()):
            self._add_favorites_button(i)

        self._list_button = RadioToolButton(icon_name='view-list')
        self._list_button.set_group(self._favorites_buttons[0])
        self._list_button.props.tooltip = _('List view')
        self._list_button.props.accelerator = \
            _('<Ctrl>%d' % (len(self._favorites_views_indicies) + 1))
        self._list_view_toggle_id = self._list_button.connect(
            'toggled', self.__view_button_toggled_cb, self._list_view_index)
        self._button_box.append(self._list_button)

        if self._favorites_buttons:
            self._favorites_buttons[0].set_active(True)

        toolitem = Gtk.Box()
        toolitem.append(self._button_box)
        toolitem.set_visible(True)
        self.append(toolitem)

        self._add_separator()

    def _add_favorites_button(self, i):
        logging.debug('adding FavoritesButton %d' % (i))
        self._favorites_buttons.append(FavoritesButton(i))
        self._favorites_buttons[i].connect('toggled',
                                           self.__view_button_toggled_cb,
                                           self._favorites_views_indicies[i])
        if i > 0:
            self._favorites_buttons[i].set_group(self._favorites_buttons[0])
        self._button_box.append(self._favorites_buttons[i])
        self._favorites_buttons[i].set_visible(True)

    def show_view_buttons(self):
        for i in range(desktop.get_number_of_views()):
            self._favorites_buttons[i].set_visible(True)
        self._list_button.set_visible(True)

    def hide_view_buttons(self):
        for i in range(desktop.get_number_of_views()):
            self._favorites_buttons[i].set_visible(False)
        self._list_button.set_visible(False)

    def clear_query(self):
        self.search_entry.props.text = ''

    def set_placeholder_text_for_view(self, view_name):
        text = _('Search in %s') % view_name
        self.search_entry.set_placeholder_text(text)

    def _add_separator(self, expand=False):
        separator = Gtk.Box()
        separator.set_visible(True)
        if expand:
            separator.set_hexpand(True)
        else:
            separator.set_size_request(style.GRID_CELL_SIZE,
                                       style.GRID_CELL_SIZE)
        self.append(separator)

    def _entry_activated_cb(self, entry):
        if self._autosearch_timer:
            GLib.source_remove(self._autosearch_timer)
            self._autosearch_timer = None
        new_query = entry.props.text
        if self._query != new_query:
            self._query = new_query
            if isinstance(self._query, bytes):
                self._query = self._query.decode()
            self.emit('query-changed', self._query)

    def _entry_changed_cb(self, entry):
        if not entry.props.text:
            entry.emit('activate')
            return

        if self._autosearch_timer:
            GLib.source_remove(self._autosearch_timer)
        self._autosearch_timer = GLib.timeout_add(_AUTOSEARCH_TIMEOUT,
                                                  self._autosearch_timer_cb)

    def _autosearch_timer_cb(self):
        logging.debug('_autosearch_timer_cb')
        self._autosearch_timer = None
        self.search_entry.emit('activate')
        return False

    def __view_button_toggled_cb(self, button, view):
        if button.props.active:
            self.emit('view-changed', view)

    def __desktop_view_icons_changed_cb(self, model):
        number_of_views = desktop.get_number_of_views()

        if len(self._favorites_views_indicies) < number_of_views:
            for i in range(number_of_views -
                           len(self._favorites_views_indicies)):
                n = len(self._favorites_views_indicies)
                self._favorites_views_indicies.append(n)
                self._add_favorites_button(n)
                self._favorites_buttons[n].set_visible(True)
        elif number_of_views < len(self._favorites_views_indicies):
            for i in range(len(self._favorites_views_indicies) -
                           number_of_views):
                n = len(self._favorites_views_indicies) - 1
                logging.debug('removing FavoritesButton %d' % (n))
                button = self._favorites_buttons[n]
                self._favorites_buttons.remove(button)
                self._button_box.remove(button)
                self._favorites_views_indicies.remove(
                    self._favorites_views_indicies[n])
        self._button_box.set_visible(True)

        self._list_view_index = number_of_views
        self._list_button.props.accelerator = \
            _('<Ctrl>%d' % (len(self._favorites_views_indicies) + 1))
        self._list_button.disconnect(self._list_view_toggle_id)
        self._list_view_toggle_id = self._list_button.connect(
            'toggled', self.__view_button_toggled_cb, self._list_view_index)
        self._list_button.set_visible(True)


class FavoritesButton(RadioToolButton):
    __gtype_name__ = 'SugarFavoritesButton'

    def __init__(self, favorite_view):
        super().__init__()

        self.props.tooltip = desktop.get_view_labels()[favorite_view]
        self.props.accelerator = _('<Ctrl>%d' % (favorite_view + 1))
        self.set_group(None)
        self.props.icon_name = desktop.get_view_icons()[favorite_view]

        favorites_settings = favoritesview.get_settings(favorite_view)
        self._layout = favorites_settings.layout

        layouts_grid = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        prev_layout_item = None
        for layoutid, layoutclass in sorted(favoritesview.LAYOUT_MAP.items()):
            layout_item = RadioToolButton(icon_name=layoutclass.icon_name,
                                          active=False)
            if prev_layout_item:
                layout_item.set_group(prev_layout_item)
            else:
                layout_item.set_group(None)
            prev_layout_item = layout_item
            if layoutid == self._layout:
                layout_item.set_active(True)
            layout_item.set_visible(True)
            layout_item.set_hexpand(True)
            layout_item.set_halign(Gtk.Align.CENTER)
            layouts_grid.append(layout_item)
            layout_item.connect('toggled', self.__layout_activate_cb,
                                layoutid, favorite_view)
        layouts_grid.set_visible(True)
        self.props.palette.set_content(layouts_grid)

    def __layout_activate_cb(self, menu_item, layout, favorite_view):
        if not menu_item.get_active():
            return
        if self._layout == layout and self.props.active:
            return

        if self._layout != layout:
            self._layout = layout

            favorites_settings = favoritesview.get_settings(favorite_view)
            favorites_settings.layout = layout

        if not self.props.active:
            self.props.active = True
        else:
            self.emit('toggled')
