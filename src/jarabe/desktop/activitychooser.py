# Copyright (C) 2016, Abhijit Patel
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

from gi.repository import GLib
from gettext import gettext as _
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject

from jarabe.util import activityfactory
from sugar4.graphics import iconentry
from sugar4.graphics import style
from sugar4.graphics.toolbutton import ToolButton

from jarabe.model import shell
from jarabe.desktop.activitieslist import ActivitiesList
from jarabe.util.normalize import normalize_string


class TitleBox(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)

        self.close_button = ToolButton(icon_name='dialog-cancel')
        self.close_button.set_tooltip(_('Close'))
        self.append(self.close_button)
        self.close_button.set_visible(True)

        self._label = Gtk.Label()
        self._label.set_halign(Gtk.Align.START)
        self._label.set_valign(Gtk.Align.CENTER)
        self._label.set_hexpand(True)

        self.append(self._label)
        self._label.set_visible(True)

    def set_title(self, title):
        self._label.set_markup('<b>%s</b>' % title)
        self._label.set_visible(True)

_AUTOSEARCH_TIMEOUT = 1000


class ActivityChooser(Gtk.Window):

    __gtype_name__ = 'ActivityChooser'

    __gsignals__ = {
        'response': (GObject.SignalFlags.RUN_FIRST, None, ([int])),
        'activity-selected': (GObject.SignalFlags.RUN_FIRST, None,
                              ([object, object])),
    }

    def __init__(self):
        super().__init__()

        self.set_decorated(False)
        self.set_resizable(False)
        self.set_modal(True)
        self.set_focusable(True)

        # Set transient parent for Wayland XDG-dialog support
        from jarabe.model import shell as _shell
        shell_model = _shell.get_model()
        if shell_model and shell_model._main_window:
            self.set_transient_for(shell_model._main_window)

        display = Gdk.Display.get_default()
        width = 1024 - style.GRID_CELL_SIZE * 2
        height = 768 - style.GRID_CELL_SIZE * 2
        if display:
            monitors = display.get_monitors()
            if monitors and monitors.get_n_items() > 0:
                geo = monitors.get_item(0).get_geometry()
                width = geo.width - style.GRID_CELL_SIZE * 2
                height = geo.height - style.GRID_CELL_SIZE * 2

        self.set_default_size(
            width * 3 / 4,
            height * 2 / 3)

        self._vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._vbox.set_margin_start(style.LINE_WIDTH)
        self._vbox.set_margin_end(style.LINE_WIDTH)
        self._vbox.set_margin_top(style.LINE_WIDTH)
        self._vbox.set_margin_bottom(style.LINE_WIDTH)
        self.set_child(self._vbox)
        self._vbox.set_visible(True)

        self._title_box = TitleBox()
        self._title_box.close_button.connect(
            'clicked',
            self.__close_button_clicked_cb)
        self._title_box.set_size_request(-1, style.GRID_CELL_SIZE)

        self._vbox.append(self._title_box)
        self._title_box.set_visible(True)

        key_controller = Gtk.EventControllerKey()
        key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_controller.connect('key-pressed', self.__key_press_event_cb)
        self.add_controller(key_controller)
        
        self.connect('realize', self.__realize_cb)

        self._list_view = ActivitiesList()

        self.search_bar = SearchBar()
        self._vbox.append(self.search_bar)
        self.search_bar.connect('query-changed',
                                self.__toolbar_query_changed_cb)
                                
        search_key_controller = Gtk.EventControllerKey()
        search_key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        search_key_controller.connect('key-pressed', self.__key_press_event_cb)
        self.search_bar.search_entry.add_controller(search_key_controller)
        self.search_bar.search_entry.grab_focus()
        
        self._scrolled_window = Gtk.ScrolledWindow()
        self._scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC,
                                         Gtk.PolicyType.AUTOMATIC)
        self._scrolled_window.set_vexpand(True)
        self._scrolled_window.set_hexpand(True)

        self._scrolled_window.set_child(self._list_view)

        self._vbox.append(self._scrolled_window)

        self._list_view.set_visible(True)
        self._list_view.connect('clear-clicked',
                                self.__activitylist_clear_clicked_cb,
                                self.search_bar)

        self.tree_view = self._list_view._tree_view

        self.tree_view.date_column.set_visible(False)
        self.tree_view.fav_column.set_visible(False)
        self.tree_view.version_column.set_visible(False)

        # Disconnect the default row-activated handler set by ActivitiesTreeView
        # so it does not also fire (double-launch). Mirrors GTK3 disconnect block.
        if self.tree_view.row_activated_handler:
            self.tree_view.disconnect(self.tree_view.row_activated_handler)
            self.tree_view.row_activated_handler = None

        self.tree_view.props.activate_on_single_click = True
        self.tree_view.connect('row-activated', self.__row_activated_cb)

        self.set_visible(True)

    def __close_button_clicked_cb(self, button):
        shell.get_model().pop_modal()
        self.destroy()

    def __realize_cb(self, widget):
        shell.get_model().push_modal()

    def __toolbar_query_changed_cb(self, toolbar, query):
        self._query = normalize_string(query.decode('utf-8'))
        self._list_view.set_filter(self._query)

        toolbar.search_entry._icon_selected = \
            self._list_view.get_activities_selected()

        # verify if one of the selected names is a perfect match
        # this is needed by the case of activities with names contained
        # in other activities like 'Paint' and 'MusicPainter'
        activity = None
        for activity in self._list_view.get_activities_selected():
            if activity['name'].upper() == query.upper():
                toolbar.search_entry._icon_selected = [activity]
                break

        # Don't change the selection if the entry has been autocompleted
        # if activity is not None and len(toolbar.search_entry._icon_selected) == 1 \
        #    and not toolbar.search_entry.get_text() == activity['name']:
        #     pos = toolbar.search_entry.get_position()
        #     toolbar.search_entry.set_text(
        #         toolbar.search_entry._icon_selected[0]['name'])
        #     toolbar.search_entry.select_region(pos, -1)

    def __key_press_event_cb(self, controller, keyval, keycode, state):
        keyname = Gdk.keyval_name(keyval)
        if keyname == 'Escape':
            shell.get_model().pop_modal()
            self.destroy()
            return True

        search_entry = self.search_bar.search_entry
        has_focus = search_entry.has_focus() or search_entry.get_focus_child() is not None
        if not has_focus:
            search_entry.grab_focus()

        widget = controller.get_widget()
        if widget == self.search_bar.search_entry:
            if keyval == Gdk.KEY_Return:
                model = self.tree_view.get_model()
                if len(model) > 1:
                    return True

                row = model[0]
                bundle_id = row[self.tree_view._model.column_bundle_id]
                activity_id = activityfactory.create_activity_id()

                self.emit('activity-selected', bundle_id, activity_id)
                shell.get_model().pop_modal()
                self.destroy()
                return True
        return False

    def __activitylist_clear_clicked_cb(self, list_view, toolbar):
        toolbar.clear_query()

    def set_title(self, text):
        self._title_box.set_title(text)

    def _got_row_tree_view(self, row):
        bundle_id = row[self.tree_view._model.column_bundle_id]
        activity_id = activityfactory.create_activity_id()
        self.emit('activity-selected', bundle_id, activity_id)
        shell.get_model().pop_modal()
        self.destroy()

    def __row_activated_cb(self, treeview, path, col):
        if col is not treeview.get_column(0):
            model = treeview.get_model()
            row = model[path]
            self._got_row_tree_view(row)
        return True


class SearchBar(Gtk.Box):
    '''
    New Toolbar below the Titlebox of sugar3.graphics PopWindow.
    This toolbar contains textentry for search.
    '''

    __gtype_name__ = 'ActivityChooserSearchBar'

    __gsignals__ = {
        'query-changed': (GObject.SignalFlags.RUN_FIRST, None,
                          ([str])),
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)

        self._query = None
        self._autosearch_timer = None

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_focusable(True)
        self.search_entry.set_width_chars(20)
        self.search_entry.connect('activate', self._entry_activated_cb)
        self.search_entry.connect('search-changed', self._entry_changed_cb)
        self.search_entry.set_hexpand(True)

        self.append(self.search_entry)
        self.search_entry.set_visible(True)
        self._add_separator()

    def clear_query(self):
        self.search_entry.props.text = ''

    def _add_separator(self, expand=False):
        separator = Gtk.Box()
        if expand:
            separator.set_hexpand(True)
        else:
            separator.set_size_request(style.GRID_CELL_SIZE,
                                       style.GRID_CELL_SIZE)
        self.append(separator)
        separator.set_visible(True)

    def _entry_activated_cb(self, entry):
        if self._autosearch_timer:
            GLib.source_remove(self._autosearch_timer)
            self._autosearch_timer = None
        new_query = entry.props.text
        if self._query != new_query:
            self._query = new_query
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
