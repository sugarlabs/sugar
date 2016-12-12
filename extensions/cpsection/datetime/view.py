# Copyright (C) 2008, OLPC
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


from gi.repository import Gtk
from gi.repository import GObject
from gettext import gettext as _

from sugar3.graphics import style
from sugar3.graphics import iconentry

from jarabe.controlpanel.sectionview import SectionView
from jarabe.controlpanel.inlinealert import InlineAlert


class TimeZone(SectionView):
    def __init__(self, model, alerts):
        SectionView.__init__(self)

        self._model = model
        self.restart_alerts = alerts
        self._zone_sid = 0
        self._cursor_change_handler = None

        self.set_border_width(style.DEFAULT_SPACING * 2)
        self.set_spacing(style.DEFAULT_SPACING)

        self.connect('realize', self.__realize_cb)

        self._entry = iconentry.IconEntry()
        self._entry.set_icon_from_name(iconentry.ICON_ENTRY_PRIMARY,
                                       'entry-search')
        self._entry.add_clear_button()
        self.pack_start(self._entry, False, False, 0)
        self._entry.show()

        self._scrolled_window = Gtk.ScrolledWindow()
        self._scrolled_window.set_policy(Gtk.PolicyType.NEVER,
                                         Gtk.PolicyType.AUTOMATIC)
        self._scrolled_window.set_shadow_type(Gtk.ShadowType.IN)

        self._store = Gtk.ListStore(GObject.TYPE_STRING)
        zones = model.read_all_timezones()
        for zone in zones:
            self._store.append([zone])

        self._treeview = Gtk.TreeView(self._store)
        self._treeview.set_search_entry(self._entry)
        self._treeview.set_search_equal_func(self._search, None)
        self._treeview.set_search_column(0)
        self._scrolled_window.add(self._treeview)
        self._treeview.show()

        self._timezone_column = Gtk.TreeViewColumn(_('Timezone'))
        self._cell = Gtk.CellRendererText()
        self._timezone_column.pack_start(self._cell, True)
        self._timezone_column.add_attribute(self._cell, 'text', 0)
        self._timezone_column.set_sort_column_id(0)
        self._treeview.append_column(self._timezone_column)

        self.pack_start(self._scrolled_window, True, True, 0)
        self._scrolled_window.show()

        self._zone_alert_box = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        self.pack_start(self._zone_alert_box, False, False, 0)

        self._zone_alert = InlineAlert()
        self._zone_alert_box.pack_start(self._zone_alert, True, True, 0)
        if 'zone' in self.restart_alerts:
            self._zone_alert.props.msg = self.restart_msg
            self._zone_alert.show()
        self._zone_alert_box.show()

        self.setup()

    def setup(self):
        zone = self._model.get_timezone()
        for row in self._store:
            if zone == row[0]:
                self._treeview.set_cursor(row.path, self._timezone_column,
                                          False)
                self._treeview.scroll_to_cell(row.path, self._timezone_column,
                                              True, 0.5, 0.5)
                break

        self.needs_restart = False
        self._cursor_change_handler = self._treeview.connect(
            'cursor-changed', self.__zone_changed_cd)

    def undo(self):
        self._treeview.disconnect(self._cursor_change_handler)
        self._model.undo()
        self._zone_alert.hide()

    def __realize_cb(self, widget):
        self._entry.grab_focus()

    def _search(self, model, column, key, iterator, data=None):
        value = model.get_value(iterator, column)
        if key.lower() in value.lower():
            return False
        return True

    def __zone_changed_cd(self, treeview, data=None):
        list_, row = treeview.get_selection().get_selected()
        if not row:
            return False
        if self._model.get_timezone() == self._store.get_value(row, 0):
            return False

        if self._zone_sid:
            GObject.source_remove(self._zone_sid)
        self._zone_sid = GObject.timeout_add(self._APPLY_TIMEOUT,
                                             self.__zone_timeout_cb, row)
        return True

    def __zone_timeout_cb(self, row):
        self._zone_sid = 0
        self._model.set_timezone(self._store.get_value(row, 0))
        self.restart_alerts.append('zone')
        self.needs_restart = True
        self._zone_alert.props.msg = self.restart_msg
        self._zone_alert.show()
        return False
