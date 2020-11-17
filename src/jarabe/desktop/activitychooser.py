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

from sugar3.activity import activityfactory
from sugar3.graphics import iconentry
from sugar3.graphics import style
from sugar3.graphics.toolbutton import ToolButton

from jarabe.model import shell
from jarabe.desktop.activitieslist import ActivitiesList
from jarabe.util.normalize import normalize_string


class TitleBox(Gtk.Toolbar):
    def __init__(self):
        Gtk.Toolbar.__init__(self)

        self.close_button = ToolButton(icon_name='dialog-cancel')
        self.close_button.set_tooltip(_('Close'))
        self.insert(self.close_button, -1)
        self.close_button.show()

        self._label = Gtk.Label()
        self._label.set_alignment(0, 0.5)

        tool_item = Gtk.ToolItem()
        tool_item.set_expand(True)
        tool_item.add(self._label)
        self._label.show()
        self.insert(tool_item, 0)
        tool_item.show()

    def set_title(self, title):
        self._label.set_markup('<b>%s</b>' % title)
        self._label.show()


_AUTOSEARCH_TIMEOUT = 1000


class ActivityChooser(Gtk.Window):

    __gtype_name__ = 'ActivityChooser'

    __gsignals__ = {
        'response': (GObject.SignalFlags.RUN_FIRST, None, ([int])),
        'activity-selected': (GObject.SignalFlags.RUN_FIRST, None,
                              ([object, object])),
    }

    def __init__(self):
        Gtk.Window.__init__(self)

        self.set_decorated(False)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_border_width(style.LINE_WIDTH)
        self.set_resizable(False)
        self.set_modal(True)
        self.set_can_focus(True)

        self._vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self._vbox)
        self._vbox.show()

        self._title_box = TitleBox()
        self._title_box.close_button.connect(
            'clicked',
            self.__close_button_clicked_cb)
        self._title_box.set_size_request(-1, style.GRID_CELL_SIZE)

        self._vbox.pack_start(self._title_box, False, True, 0)
        self._title_box.show()

        self.set_size_request(
            (Gdk.Screen.height() - style.GRID_CELL_SIZE * 3) * 3 / 4,
            (Gdk.Screen.height() - style.GRID_CELL_SIZE * 2) * 2 / 3)
        self.connect('key-press-event', self.__key_press_event_cb)
        self.connect('realize', self.__realize_cb)

        self._list_view = ActivitiesList()

        self.search_bar = SearchBar()
        self._vbox.pack_start(self.search_bar, False, False, 0)
        self.search_bar.connect('query-changed',
                                self.__toolbar_query_changed_cb)
        self.search_bar.search_entry.connect('key-press-event',
                                             self.__key_press_event_cb)
        self.search_bar.search_entry.grab_focus()
        self._scrolled_window = Gtk.ScrolledWindow()
        self._scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC,
                                         Gtk.PolicyType.AUTOMATIC)

        self._scrolled_window.add(self._list_view)

        self._vbox.pack_start(self._scrolled_window, True, True, 0)

        self._list_view.show()
        self._list_view.connect('clear-clicked',
                                self.__activitylist_clear_clicked_cb,
                                self.search_bar)

        self.tree_view = self._list_view._tree_view

        self.tree_view.date_column.set_visible(False)
        self.tree_view.fav_column.set_visible(False)
        self.tree_view.version_column.set_visible(False)

        if self.tree_view.row_activated_handler:
            self.tree_view.disconnect(self.tree_view.row_activated_handler)
        if self.tree_view.button_press_handler:
            self.tree_view.disconnect(self.tree_view.button_press_handler)
        if self.tree_view.button_reslease_handler:
            self.tree_view.disconnect(self.tree_view.button_reslease_handler)
        if self.tree_view.icon_clicked_handler:
            self.tree_view.disconnect(self.tree_view.icon_clicked_handler)

        if hasattr(self.tree_view.props, 'activate_on_single_click'):
            # Gtk+ 3.8 and later
            self.tree_view.props.activate_on_single_click = True
            self.tree_view.connect('row-activated', self.__row_activated_cb)
        else:
            self.tree_view.cell_icon.connect('clicked',
                                             self.__icon_clicked_cb)
            self.tree_view.connect('button-press-event',
                                   self.__button_press_cb)
            self.tree_view.connect('button-release-event',
                                   self.__button_release_cb)
            self._row_activated_armed_path = None

        self.show()

    def __close_button_clicked_cb(self, button):
        self.destroy()

    def __realize_cb(self, widget):
        shell.get_model().push_modal()
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        window = self.get_window()
        window.set_accept_focus(True)
        shell.get_model().push_modal()

    def __toolbar_query_changed_cb(self, toolbar, query):
        self._query = normalize_string(query.decode('utf-8'))
        self._list_view.set_filter(self._query)

        toolbar.search_entry._icon_selected = \
            self._list_view.get_activities_selected()

        # verify if one off the selected names is a perfect match
        # this is needed by th case of activities with names contained
        # in other activities like 'Paint' and 'MusicPainter'
        for activity in self._list_view.get_activities_selected():
            if activity['name'].upper() == query.upper():
                toolbar.search_entry._icon_selected = [activity]
                break

        # Don't change the selection if the entry has been autocompleted
        if len(toolbar.search_entry._icon_selected) == 1 \
           and not toolbar.search_entry.get_text() == activity['name']:
            pos = toolbar.search_entry.get_position()
            toolbar.search_entry.set_text(
                toolbar.search_entry._icon_selected[0]['name'])
            toolbar.search_entry.select_region(pos, -1)

    def __key_press_event_cb(self, widget, event):
        keyname = Gdk.keyval_name(event.keyval)
        if keyname == 'Escape':
            self.destroy()

        if not self.search_bar.search_entry.has_focus():
            self.search_bar.search_entry.grab_focus()

        if widget == self.search_bar.search_entry:
            if event.keyval == Gdk.KEY_Return:
                model = self.tree_view.get_model()
                if len(model) > 1:
                    return True

                row = model[0]
                bundle_id = row[self.tree_view._model.column_bundle_id]
                activity_id = activityfactory.create_activity_id()

                self.emit('activity-selected', bundle_id, activity_id)
                self.destroy()
                return True

    @staticmethod
    def __activitylist_clear_clicked_cb(list_view, toolbar):
        toolbar.clear_query()

    def set_title(self, text):
        self._title_box.set_title(text)

    def _got_row_tree_view(self, row):
        bundle_id = row[self.tree_view._model.column_bundle_id]
        activity_id = activityfactory.create_activity_id()
        self.emit('activity-selected', bundle_id, activity_id)
        self.destroy()

    def __button_press_cb(self, widget, event):
        path = self.tree_view.__button_to_path(event,
                                               Gdk.EventType.BUTTON_PRESS)
        if path is None:
            return

        self._row_activated_armed_path = path

    def __button_release_cb(self, widget, event):
        path = self.tree_view.__button_to_path(event,
                                               Gdk.EventType.BUTTON_PRESS)
        if path is None:
            return

        if self._row_activated_armed_path != path:
            return

        model = self.tree_view.get_model()
        row = model[path]
        self._got_row_tree_view(row)
        self._row_activated_armed_path = None

    def __icon_clicked_cb(self, tree_view, path):
        model = tree_view.get_model()
        row = model[path]
        self._got_row_tree_view(row)
        return True

    def __row_activated_cb(self, treeview, path, col):
        if col is not treeview.get_column(0):
            model = treeview.get_model()
            row = model[path]
            self._got_row_tree_view(row)
        return True


class SearchBar(Gtk.Toolbar):
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
        Gtk.Toolbar.__init__(self)

        self._query = None
        self._autosearch_timer = None
        # self.set_border_width(10)
        tool_item = Gtk.ToolItem()
        self.insert(tool_item, -1)
        tool_item.set_expand(True)
        tool_item.show()

        self.search_entry = iconentry.IconEntry()
        self.search_entry.set_icon_from_name(iconentry.ICON_ENTRY_PRIMARY,
                                             'entry-search')
        self.search_entry.set_can_focus(True)
        self.search_entry.add_clear_button()
        self.search_entry.set_width_chars(20)
        self.search_entry.connect('activate', self._entry_activated_cb)
        self.search_entry.connect('changed', self._entry_changed_cb)

        tool_item.add(self.search_entry)
        self.search_entry.show()
        self._add_separator()

    def clear_query(self):
        self.search_entry.props.text = ''

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
            GLib.source_remove(self._autosearch_timer)
            self._autosearch_timer = None
        new_query = entry.props.text
        if self._query != new_query:
            self._query = new_query
            self.emit('query-changed', self._query)

    def _entry_changed_cb(self, entry):
        if not entry.props.text:
            entry.activate()
            return

        if self._autosearch_timer:
            GLib.source_remove(self._autosearch_timer)
        self._autosearch_timer = GLib.timeout_add(_AUTOSEARCH_TIMEOUT,
                                                  self._autosearch_timer_cb)

    def _autosearch_timer_cb(self):
        logging.debug('_autosearch_timer_cb')
        self._autosearch_timer = None
        self.search_entry.activate()
        return False
