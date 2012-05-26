# Copyright (C) 2008 One Laptop Per Child
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
import os

import gobject
import gtk

from sugar.graphics import style
from sugar.graphics import iconentry
from sugar.graphics.radiotoolbutton import RadioToolButton
from sugar.graphics.alert import Alert
from sugar.graphics.icon import Icon

from jarabe.desktop import favoritesview
from jarabe.desktop.activitieslist import ActivitiesList


_FAVORITES_VIEW = 0
_LIST_VIEW = 1

_AUTOSEARCH_TIMEOUT = 1000


class HomeBox(gtk.VBox):
    __gtype_name__ = 'SugarHomeBox'

    def __init__(self):
        logging.debug('STARTUP: Loading the home view')

        gobject.GObject.__init__(self)

        self._favorites_view = favoritesview.FavoritesView()
        self._list_view = ActivitiesList()

        self._toolbar = HomeToolbar()
        self._toolbar.connect('query-changed', self.__toolbar_query_changed_cb)
        self._toolbar.connect('view-changed', self.__toolbar_view_changed_cb)
        self.pack_start(self._toolbar, expand=False)
        self._toolbar.show()

        self._set_view(_FAVORITES_VIEW)
        self._query = ''

    def show_software_updates_alert(self):
        alert = Alert()
        updater_icon = Icon(icon_name='module-updater',
                            pixel_size=style.STANDARD_ICON_SIZE)
        alert.props.icon = updater_icon
        updater_icon.show()
        alert.props.title = _('Software Update')
        alert.props.msg = _('Update your activities to ensure'
                            ' compatibility with your new software')

        cancel_icon = Icon(icon_name='dialog-cancel')
        alert.add_button(gtk.RESPONSE_CANCEL, _('Cancel'), cancel_icon)

        alert.add_button(gtk.RESPONSE_REJECT, _('Later'))

        erase_icon = Icon(icon_name='dialog-ok')
        alert.add_button(gtk.RESPONSE_OK, _('Check now'), erase_icon)

        if self._list_view in self.get_children():
            self._list_view.add_alert(alert)
        else:
            self._favorites_view.add_alert(alert)
        alert.connect('response', self.__software_update_response_cb)

    def __software_update_response_cb(self, alert, response_id):
        if self._list_view in self.get_children():
            self._list_view.remove_alert()
        else:
            self._favorites_view.remove_alert()

        if response_id != gtk.RESPONSE_REJECT:
            update_trigger_file = os.path.expanduser('~/.sugar-update')
            try:
                os.unlink(update_trigger_file)
            except OSError:
                logging.error('Software-update: Can not remove file %s',
                    update_trigger_file)

        if response_id == gtk.RESPONSE_OK:
            from jarabe.controlpanel.gui import ControlPanel
            panel = ControlPanel()
            panel.set_transient_for(self.get_toplevel())
            panel.show()
            panel.show_section_view('updater')
            panel.set_section_view_auto_close()

    def __toolbar_query_changed_cb(self, toolbar, query):
        self._query = query.lower()
        self._list_view.set_filter(self._query)
        self._favorites_view.set_filter(self._query)

    def __toolbar_view_changed_cb(self, toolbar, view):
        self._set_view(view)

    def _set_view(self, view):
        if view == _FAVORITES_VIEW:
            if self._list_view in self.get_children():
                self.remove(self._list_view)

            if self._favorites_view not in self.get_children():
                self.add(self._favorites_view)
                self._favorites_view.show()
        elif view == _LIST_VIEW:
            if self._favorites_view in self.get_children():
                self.remove(self._favorites_view)

            if self._list_view not in self.get_children():
                self.add(self._list_view)
                self._list_view.show()
        else:
            raise ValueError('Invalid view: %r' % view)

    _REDRAW_TIMEOUT = 5 * 60 * 1000  # 5 minutes

    def resume(self):
        pass

    def suspend(self):
        pass

    def has_activities(self):
        # TODO: Do we need this?
        #return self._donut.has_activities()
        return False

    def focus_search_entry(self):
        self._toolbar.search_entry.grab_focus()

    def set_resume_mode(self, resume_mode):
        self._favorites_view.set_resume_mode(resume_mode)
        if resume_mode and self._query != '':
            self._list_view.set_filter(self._query)
            self._favorites_view.set_filter(self._query)


class HomeToolbar(gtk.Toolbar):
    __gtype_name__ = 'SugarHomeToolbar'

    __gsignals__ = {
        'query-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                          ([str])),
        'view-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                         ([object])),
    }

    def __init__(self):
        gtk.Toolbar.__init__(self)

        self._query = None
        self._autosearch_timer = None

        self._add_separator()

        tool_item = gtk.ToolItem()
        self.insert(tool_item, -1)
        tool_item.show()

        self.search_entry = iconentry.IconEntry()
        self.search_entry.set_icon_from_name(iconentry.ICON_ENTRY_PRIMARY,
                                              'system-search')
        self.search_entry.add_clear_button()
        self.search_entry.set_width_chars(25)
        self.search_entry.connect('activate', self.__entry_activated_cb)
        self.search_entry.connect('changed', self.__entry_changed_cb)
        tool_item.add(self.search_entry)
        self.search_entry.show()

        self._add_separator(expand=True)

        favorites_button = FavoritesButton()
        favorites_button.connect('toggled', self.__view_button_toggled_cb,
                                 _FAVORITES_VIEW)
        self.insert(favorites_button, -1)
        favorites_button.show()

        self._list_button = RadioToolButton(named_icon='view-list')
        self._list_button.props.group = favorites_button
        self._list_button.props.tooltip = _('List view')
        self._list_button.props.accelerator = _('<Ctrl>2')
        self._list_button.connect('toggled', self.__view_button_toggled_cb,
                            _LIST_VIEW)
        self.insert(self._list_button, -1)
        self._list_button.show()

        self._add_separator()

    def __view_button_toggled_cb(self, button, view):
        if button.props.active:
            self.search_entry.grab_focus()
            self.emit('view-changed', view)

    def _add_separator(self, expand=False):
        separator = gtk.SeparatorToolItem()
        separator.props.draw = False
        if expand:
            separator.set_expand(True)
        else:
            separator.set_size_request(style.GRID_CELL_SIZE,
                                       style.GRID_CELL_SIZE)
        self.insert(separator, -1)
        separator.show()

    def __entry_activated_cb(self, entry):
        if self._autosearch_timer:
            gobject.source_remove(self._autosearch_timer)
        new_query = entry.props.text
        if self._query != new_query:
            self._query = new_query

            self.emit('query-changed', self._query)

    def __entry_changed_cb(self, entry):
        if not entry.props.text:
            entry.activate()
            return

        if self._autosearch_timer:
            gobject.source_remove(self._autosearch_timer)
        self._autosearch_timer = gobject.timeout_add(_AUTOSEARCH_TIMEOUT,
            self.__autosearch_timer_cb)

    def __autosearch_timer_cb(self):
        self._autosearch_timer = None
        self.search_entry.activate()
        return False


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

        # someday, this will be a gtk.Table()
        layouts_grid = gtk.HBox()
        layout_item = None
        for layoutid, layoutclass in sorted(favoritesview.LAYOUT_MAP.items()):
            layout_item = RadioToolButton(icon_name=layoutclass.icon_name,
                                          group=layout_item, active=False)
            if layoutid == self._layout:
                layout_item.set_active(True)
            layouts_grid.pack_start(layout_item, fill=False)
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
        self.props.named_icon = favoritesview.LAYOUT_MAP[self._layout]\
                                .icon_name
