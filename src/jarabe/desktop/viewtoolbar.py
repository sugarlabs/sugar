# Copyright (C) 2006-2007 Red Hat, Inc.
# Copyright (C) 2009 Tomeu Vizoso, Simon Schampijer
# Copyright (C) 2009-2012 One Laptop per Child
# Copyright (C) 2010 Collabora Ltd. <http://www.collabora.co.uk/>
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
import logging

from gi.repository import Gtk
from gi.repository import GObject

from sugar3.graphics import style
from sugar3.graphics import iconentry
from sugar3.graphics.radiotoolbutton import RadioToolButton

from jarabe.desktop import favoritesview

_AUTOSEARCH_TIMEOUT = 1000
_FAVORITES_VIEW = 0
_LIST_VIEW = 1


class ViewToolbar(Gtk.Toolbar):
    __gtype_name__ = 'SugarViewToolbar'

    __gsignals__ = {
        'query-changed': (GObject.SignalFlags.RUN_FIRST, None,
                          ([str])),
        'view-changed': (GObject.SignalFlags.RUN_FIRST, None,
                         ([object])),
    }

    def __init__(self):
        Gtk.Toolbar.__init__(self)

        self._query = None
        self._autosearch_timer = None

        self._add_separator()

        tool_item = Gtk.ToolItem()
        self.insert(tool_item, -1)
        tool_item.show()

        self.search_entry = iconentry.IconEntry()
        self.search_entry.set_icon_from_name(iconentry.ICON_ENTRY_PRIMARY,
                                             'system-search')
        self.set_placeholder_text_for_view(_('Home'))
        self.search_entry.add_clear_button()
        self.search_entry.set_width_chars(25)
        self.search_entry.connect('activate', self._entry_activated_cb)
        self.search_entry.connect('changed', self._entry_changed_cb)
        tool_item.add(self.search_entry)
        self.search_entry.show()

        self._add_separator(expand=True)

        self._favorites_button = FavoritesButton()
        self._favorites_button.connect('toggled',
                                       self.__view_button_toggled_cb,
                                       _FAVORITES_VIEW)
        self.insert(self._favorites_button, -1)

        self._list_button = RadioToolButton(icon_name='view-list')
        self._list_button.props.group = self._favorites_button
        self._list_button.props.tooltip = _('List view')
        self._list_button.props.accelerator = _('<Ctrl>2')
        self._list_button.connect('toggled', self.__view_button_toggled_cb,
                                      _LIST_VIEW)
        self.insert(self._list_button, -1)

        self._add_separator()

    def show_view_buttons(self):
        self._favorites_button.show()
        self._list_button.show()

    def hide_view_buttons(self):
        self._favorites_button.hide()
        self._list_button.hide()

    def clear_query(self):
        self.search_entry.props.text = ''

    def set_placeholder_text_for_view(self, view_name):
        text = _('Search in %s') % view_name
        self.search_entry.set_placeholder_text(text)

    def _add_separator(self, expand=False):
        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        if expand:
            separator.set_expand(True)
        else:
            separator.set_size_request(style.GRID_CELL_SIZE,
                                       style.GRID_CELL_SIZE)
        self.insert(separator, -1)
        separator.show()

    def _entry_activated_cb(self, entry):
        if self._autosearch_timer:
            GObject.source_remove(self._autosearch_timer)
        new_query = entry.props.text
        if self._query != new_query:
            self._query = new_query
            self.emit('query-changed', self._query)

    def _entry_changed_cb(self, entry):
        if not entry.props.text:
            entry.activate()
            return

        if self._autosearch_timer:
            GObject.source_remove(self._autosearch_timer)
        self._autosearch_timer = GObject.timeout_add(_AUTOSEARCH_TIMEOUT,
                                                     self._autosearch_timer_cb)

    def _autosearch_timer_cb(self):
        logging.debug('_autosearch_timer_cb')
        self._autosearch_timer = None
        self.search_entry.activate()
        return False

    def __view_button_toggled_cb(self, button, view):
        if button.props.active:
            self.emit('view-changed', view)


class FavoritesButton(RadioToolButton):
    __gtype_name__ = 'SugarFavoritesButton'

    def __init__(self):
        RadioToolButton.__init__(self)

        self.props.tooltip = _('Favorites view')
        self.props.accelerator = _('<Ctrl>1')
        self.props.group = None

        favorites_settings = favoritesview.get_settings()
        self._layout = favorites_settings.layout
        self._update_icon()

        # someday, this will be a Gtk.Table()
        layouts_grid = Gtk.HBox()
        layout_item = None
        for layoutid, layoutclass in sorted(favoritesview.LAYOUT_MAP.items()):
            layout_item = RadioToolButton(icon_name=layoutclass.icon_name,
                                          group=layout_item, active=False)
            if layoutid == self._layout:
                layout_item.set_active(True)
            layouts_grid.pack_start(layout_item, True, False, 0)
            layout_item.connect('toggled', self.__layout_activate_cb,
                                layoutid)
        layouts_grid.show_all()
        self.props.palette.set_content(layouts_grid)

    def __layout_activate_cb(self, menu_item, layout):
        if not menu_item.get_active():
            return
        if self._layout == layout and self.props.active:
            return

        if self._layout != layout:
            self._layout = layout
            self._update_icon()

            favorites_settings = favoritesview.get_settings()
            favorites_settings.layout = layout

        if not self.props.active:
            self.props.active = True
        else:
            self.emit('toggled')

    def _update_icon(self):
        self.props.icon_name = favoritesview.LAYOUT_MAP[self._layout].icon_name
