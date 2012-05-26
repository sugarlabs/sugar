# Copyright (C) 2007, One Laptop Per Child
# Copyright (C) 2009, Walter Bender
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
from datetime import datetime, timedelta
import os
import gconf
import time

import gobject
import gio
import glib
import gtk

from sugar.graphics.palette import Palette
from sugar.graphics.toolbox import Toolbox
from sugar.graphics.toolcombobox import ToolComboBox
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.toggletoolbutton import ToggleToolButton
from sugar.graphics.combobox import ComboBox
from sugar.graphics.menuitem import MenuItem
from sugar.graphics.icon import Icon
from sugar.graphics.xocolor import XoColor
from sugar.graphics import iconentry
from sugar.graphics import style
from sugar import mime

from jarabe.model import bundleregistry
from jarabe.journal import misc
from jarabe.journal import model
from jarabe.journal.palettes import ClipboardMenu
from jarabe.journal.palettes import VolumeMenu


_AUTOSEARCH_TIMEOUT = 1000

_ACTION_ANYTIME = 0
_ACTION_TODAY = 1
_ACTION_SINCE_YESTERDAY = 2
_ACTION_PAST_WEEK = 3
_ACTION_PAST_MONTH = 4
_ACTION_PAST_YEAR = 5

_ACTION_ANYTHING = 0

_ACTION_EVERYBODY = 0
_ACTION_MY_FRIENDS = 1
_ACTION_MY_CLASS = 2


class MainToolbox(Toolbox):
    def __init__(self):
        Toolbox.__init__(self)

        self.search_toolbar = SearchToolbar()
        self.search_toolbar.set_size_request(-1, style.GRID_CELL_SIZE)
        self.add_toolbar(_('Search'), self.search_toolbar)
        self.search_toolbar.show()


class SearchToolbar(gtk.Toolbar):
    __gtype_name__ = 'SearchToolbar'

    __gsignals__ = {
        'query-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                          ([object])),
        }

    def __init__(self):
        gtk.Toolbar.__init__(self)

        self._mount_point = None

        self._search_entry = iconentry.IconEntry()
        self._search_entry.set_icon_from_name(iconentry.ICON_ENTRY_PRIMARY,
                                              'system-search')
        self._search_entry.connect('activate', self._search_entry_activated_cb)
        self._search_entry.connect('changed', self._search_entry_changed_cb)
        self._search_entry.add_clear_button()
        self._autosearch_timer = None
        self._add_widget(self._search_entry, expand=True)

        self._favorite_button = ToggleToolButton('emblem-favorite')
        self._favorite_button.connect('toggled',
                                      self.__favorite_button_toggled_cb)
        self.insert(self._favorite_button, -1)
        self._favorite_button.show()

        self._what_search_combo = ComboBox()
        self._what_combo_changed_sid = self._what_search_combo.connect(
                'changed', self._combo_changed_cb)
        tool_item = ToolComboBox(self._what_search_combo)
        self.insert(tool_item, -1)
        tool_item.show()

        self._when_search_combo = self._get_when_search_combo()
        tool_item = ToolComboBox(self._when_search_combo)
        self.insert(tool_item, -1)
        tool_item.show()

        self._sorting_button = SortingButton()
        self._sorting_button.connect('clicked',
                                     self.__sorting_button_clicked_cb)
        self.insert(self._sorting_button, -1)
        self._sorting_button.connect('sort-property-changed',
                                     self.__sort_changed_cb)
        self._sorting_button.show()

        # TODO: enable it when the DS supports saving the buddies.
        #self._with_search_combo = self._get_with_search_combo()
        #tool_item = ToolComboBox(self._with_search_combo)
        #self.insert(tool_item, -1)
        #tool_item.show()

        self._query = self._build_query()

        self.refresh_filters()

    def give_entry_focus(self):
        self._search_entry.grab_focus()

    def _get_when_search_combo(self):
        when_search = ComboBox()
        when_search.append_item(_ACTION_ANYTIME, _('Anytime'))
        when_search.append_separator()
        when_search.append_item(_ACTION_TODAY, _('Today'))
        when_search.append_item(_ACTION_SINCE_YESTERDAY,
                                      _('Since yesterday'))
        # TRANS: Filter entries modified during the last 7 days.
        when_search.append_item(_ACTION_PAST_WEEK, _('Past week'))
        # TRANS: Filter entries modified during the last 30 days.
        when_search.append_item(_ACTION_PAST_MONTH, _('Past month'))
        # TRANS: Filter entries modified during the last 356 days.
        when_search.append_item(_ACTION_PAST_YEAR, _('Past year'))
        when_search.set_active(0)
        when_search.connect('changed', self._combo_changed_cb)
        return when_search

    def _get_with_search_combo(self):
        with_search = ComboBox()
        with_search.append_item(_ACTION_EVERYBODY, _('Anyone'))
        with_search.append_separator()
        with_search.append_item(_ACTION_MY_FRIENDS, _('My friends'))
        with_search.append_item(_ACTION_MY_CLASS, _('My class'))
        with_search.append_separator()

        # TODO: Ask the model for buddies.
        with_search.append_item(3, 'Dan', 'theme:xo')

        with_search.set_active(0)
        with_search.connect('changed', self._combo_changed_cb)
        return with_search

    def _add_widget(self, widget, expand=False):
        tool_item = gtk.ToolItem()
        tool_item.set_expand(expand)

        tool_item.add(widget)
        widget.show()

        self.insert(tool_item, -1)
        tool_item.show()

    def _build_query(self):
        query = {}

        if self._mount_point:
            query['mountpoints'] = [self._mount_point]

        if self._favorite_button.props.active:
            query['keep'] = 1

        if self._what_search_combo.props.value:
            value = self._what_search_combo.props.value
            generic_type = mime.get_generic_type(value)
            if generic_type:
                mime_types = generic_type.mime_types
                query['mime_type'] = mime_types
            else:
                query['activity'] = self._what_search_combo.props.value

        if self._when_search_combo.props.value:
            date_from, date_to = self._get_date_range()
            query['timestamp'] = {'start': date_from, 'end': date_to}

        if self._search_entry.props.text:
            text = self._search_entry.props.text.strip()
            if text:
                query['query'] = text

        property_, order = self._sorting_button.get_current_sort()

        if order == gtk.SORT_ASCENDING:
            sign = '+'
        else:
            sign = '-'
        query['order_by'] = [sign + property_]

        return query

    def _get_date_range(self):
        today_start = datetime.today().replace(hour=0, minute=0, second=0)
        right_now = datetime.today()
        if self._when_search_combo.props.value == _ACTION_TODAY:
            date_range = (today_start, right_now)
        elif self._when_search_combo.props.value == _ACTION_SINCE_YESTERDAY:
            date_range = (today_start - timedelta(1), right_now)
        elif self._when_search_combo.props.value == _ACTION_PAST_WEEK:
            date_range = (today_start - timedelta(7), right_now)
        elif self._when_search_combo.props.value == _ACTION_PAST_MONTH:
            date_range = (today_start - timedelta(30), right_now)
        elif self._when_search_combo.props.value == _ACTION_PAST_YEAR:
            date_range = (today_start - timedelta(356), right_now)

        return (time.mktime(date_range[0].timetuple()),
                time.mktime(date_range[1].timetuple()))

    def _combo_changed_cb(self, combo):
        self._update_if_needed()

    def __sort_changed_cb(self, button):
        self._update_if_needed()

    def __sorting_button_clicked_cb(self, button):
        self._sorting_button.palette.popup(immediate=True, state=1)

    def _update_if_needed(self):
        new_query = self._build_query()
        if self._query != new_query:
            self._query = new_query
            self.emit('query-changed', self._query)

    def _search_entry_activated_cb(self, search_entry):
        if self._autosearch_timer:
            gobject.source_remove(self._autosearch_timer)
        new_query = self._build_query()
        if self._query != new_query:
            self._query = new_query
            self.emit('query-changed', self._query)

    def _search_entry_changed_cb(self, search_entry):
        if not search_entry.props.text:
            search_entry.activate()
            return

        if self._autosearch_timer:
            gobject.source_remove(self._autosearch_timer)
        self._autosearch_timer = gobject.timeout_add(_AUTOSEARCH_TIMEOUT,
                                                     self._autosearch_timer_cb)

    def _autosearch_timer_cb(self):
        logging.debug('_autosearch_timer_cb')
        self._autosearch_timer = None
        self._search_entry.activate()
        return False

    def set_mount_point(self, mount_point):
        self._mount_point = mount_point
        new_query = self._build_query()
        if self._query != new_query:
            self._query = new_query
            self.emit('query-changed', self._query)

    def set_what_filter(self, what_filter):
        combo_model = self._what_search_combo.get_model()
        what_filter_index = -1
        for i in range(0, len(combo_model) - 1):
            if combo_model[i][0] == what_filter:
                what_filter_index = i
                break

        if what_filter_index == -1:
            logging.warning('what_filter %r not known', what_filter)
        else:
            self._what_search_combo.set_active(what_filter_index)

    def refresh_filters(self):
        current_value = self._what_search_combo.props.value
        current_value_index = 0

        self._what_search_combo.handler_block(self._what_combo_changed_sid)
        try:
            self._what_search_combo.remove_all()
            # TRANS: Item in a combo box that filters by entry type.
            self._what_search_combo.append_item(_ACTION_ANYTHING,
                                                _('Anything'))

            registry = bundleregistry.get_registry()
            appended_separator = False

            types = mime.get_all_generic_types()
            for generic_type in types:
                if not appended_separator:
                    self._what_search_combo.append_separator()
                    appended_separator = True
                self._what_search_combo.append_item(
                    generic_type.type_id, generic_type.name, generic_type.icon)
                if generic_type.type_id == current_value:
                    current_value_index = \
                            len(self._what_search_combo.get_model()) - 1

                self._what_search_combo.set_active(current_value_index)

            self._what_search_combo.append_separator()

            for service_name in model.get_unique_values('activity'):
                activity_info = registry.get_bundle(service_name)
                if activity_info is None:
                    continue

                if service_name == current_value:
                    combo_model = self._what_search_combo.get_model()
                    current_value_index = len(combo_model)

                # try activity-provided icon
                if os.path.exists(activity_info.get_icon()):
                    try:
                        self._what_search_combo.append_item(service_name,
                                activity_info.get_name(),
                                file_name=activity_info.get_icon())
                    except glib.GError, exception:
                        logging.warning('Falling back to default icon for'
                                        ' "what" filter because %r (%r) has an'
                                        ' invalid icon: %s',
                                        activity_info.get_name(),
                                        str(service_name), exception)
                    else:
                        continue

                # fall back to generic icon
                self._what_search_combo.append_item(service_name,
                        activity_info.get_name(),
                        icon_name='application-octet-stream')

        finally:
            self._what_search_combo.handler_unblock(
                    self._what_combo_changed_sid)

    def __favorite_button_toggled_cb(self, favorite_button):
        self._update_if_needed()

    def clear_query(self):
        self._search_entry.props.text = ''
        self._what_search_combo.set_active(0)
        self._when_search_combo.set_active(0)
        self._favorite_button.props.active = False


class DetailToolbox(Toolbox):
    def __init__(self):
        Toolbox.__init__(self)

        self.entry_toolbar = EntryToolbar()
        self.add_toolbar('', self.entry_toolbar)
        self.entry_toolbar.show()


class EntryToolbar(gtk.Toolbar):
    __gsignals__ = {
        'volume-error': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                         ([str, str])),
        }

    def __init__(self):
        gtk.Toolbar.__init__(self)

        self._metadata = None
        self._temp_file_path = None

        self._resume = ToolButton('activity-start')
        self._resume.connect('clicked', self._resume_clicked_cb)
        self.add(self._resume)
        self._resume.show()

        client = gconf.client_get_default()
        color = XoColor(client.get_string('/desktop/sugar/user/color'))
        self._copy = ToolButton()
        icon = Icon(icon_name='edit-copy', xo_color=color)
        self._copy.set_icon_widget(icon)
        icon.show()
        self._copy.set_tooltip(_('Copy to'))
        self._copy.connect('clicked', self._copy_clicked_cb)
        self.add(self._copy)
        self._copy.show()

        self._duplicate = ToolButton()
        icon = Icon(icon_name='edit-duplicate', xo_color=color)
        self._duplicate.set_icon_widget(icon)
        self._duplicate.set_tooltip(_('Duplicate'))
        self._duplicate.connect('clicked', self._duplicate_clicked_cb)
        self.add(self._duplicate)

        separator = gtk.SeparatorToolItem()
        self.add(separator)
        separator.show()

        erase_button = ToolButton('list-remove')
        erase_button.set_tooltip(_('Erase'))
        erase_button.connect('clicked', self._erase_button_clicked_cb)
        self.add(erase_button)
        erase_button.show()

    def set_metadata(self, metadata):
        self._metadata = metadata
        self._refresh_copy_palette()
        self._refresh_duplicate_palette()
        self._refresh_resume_palette()

    def _resume_clicked_cb(self, button):
        misc.resume(self._metadata)

    def _copy_clicked_cb(self, button):
        button.palette.popup(immediate=True, state=Palette.SECONDARY)

    def _duplicate_clicked_cb(self, button):
        file_path = model.get_file(self._metadata['uid'])
        try:
            model.copy(self._metadata, '/')
        except IOError, e:
            logging.exception('Error while copying the entry.')
            self.emit('volume-error',
                      _('Error while copying the entry. %s') % (e.strerror, ),
                      _('Error'))

    def _erase_button_clicked_cb(self, button):
        registry = bundleregistry.get_registry()

        bundle = misc.get_bundle(self._metadata)
        if bundle is not None and registry.is_installed(bundle):
            registry.uninstall(bundle)
        model.delete(self._metadata['uid'])

    def _resume_menu_item_activate_cb(self, menu_item, service_name):
        misc.resume(self._metadata, service_name)

    def _refresh_copy_palette(self):
        palette = self._copy.get_palette()

        for menu_item in palette.menu.get_children():
            palette.menu.remove(menu_item)
            menu_item.destroy()

        clipboard_menu = ClipboardMenu(self._metadata)
        clipboard_menu.set_image(Icon(icon_name='toolbar-edit',
                                      icon_size=gtk.ICON_SIZE_MENU))
        clipboard_menu.connect('volume-error', self.__volume_error_cb)
        palette.menu.append(clipboard_menu)
        clipboard_menu.show()

        if self._metadata['mountpoint'] != '/':
            client = gconf.client_get_default()
            color = XoColor(client.get_string('/desktop/sugar/user/color'))
            journal_menu = VolumeMenu(self._metadata, _('Journal'), '/')
            journal_menu.set_image(Icon(icon_name='activity-journal',
                                        xo_color=color,
                                        icon_size=gtk.ICON_SIZE_MENU))
            journal_menu.connect('volume-error', self.__volume_error_cb)
            palette.menu.append(journal_menu)
            journal_menu.show()

        volume_monitor = gio.volume_monitor_get()
        icon_theme = gtk.icon_theme_get_default()
        for mount in volume_monitor.get_mounts():
            if self._metadata['mountpoint'] == mount.get_root().get_path():
                continue
            volume_menu = VolumeMenu(self._metadata, mount.get_name(),
                                     mount.get_root().get_path())
            for name in mount.get_icon().props.names:
                if icon_theme.has_icon(name):
                    volume_menu.set_image(Icon(icon_name=name,
                                               icon_size=gtk.ICON_SIZE_MENU))
                    break
            volume_menu.connect('volume-error', self.__volume_error_cb)
            palette.menu.append(volume_menu)
            volume_menu.show()

    def _refresh_duplicate_palette(self):
        color = misc.get_icon_color(self._metadata)
        self._copy.get_icon_widget().props.xo_color = color
        if self._metadata['mountpoint'] == '/':
            self._duplicate.show()
            icon = self._duplicate.get_icon_widget()
            icon.props.xo_color = color
            icon.show()
        else:
            self._duplicate.hide()

    def __volume_error_cb(self, menu_item, message, severity):
        self.emit('volume-error', message, severity)

    def _refresh_resume_palette(self):
        if self._metadata.get('activity_id', ''):
            # TRANS: Action label for resuming an activity.
            self._resume.set_tooltip(_('Resume'))
        else:
            # TRANS: Action label for starting an entry.
            self._resume.set_tooltip(_('Start'))

        palette = self._resume.get_palette()

        for menu_item in palette.menu.get_children():
            palette.menu.remove(menu_item)
            menu_item.destroy()

        for activity_info in misc.get_activities(self._metadata):
            menu_item = MenuItem(activity_info.get_name())
            menu_item.set_image(Icon(file=activity_info.get_icon(),
                                        icon_size=gtk.ICON_SIZE_MENU))
            menu_item.connect('activate', self._resume_menu_item_activate_cb,
                                activity_info.get_bundle_id())
            palette.menu.append(menu_item)
            menu_item.show()


class SortingButton(ToolButton):
    __gtype_name__ = 'JournalSortingButton'

    __gsignals__ = {
        'sort-property-changed': (gobject.SIGNAL_RUN_FIRST,
                                  gobject.TYPE_NONE,
                                  ([])),
    }

    _SORT_OPTIONS = [
        ('timestamp', 'view-lastedit', _('Sort by date modified')),
        ('creation_time', 'view-created', _('Sort by date created')),
        ('filesize', 'view-size', _('Sort by size')),
    ]

    def __init__(self):
        ToolButton.__init__(self)

        self._property = 'timestamp'
        self._order = gtk.SORT_ASCENDING

        self.props.tooltip = _('Sort view')
        self.props.icon_name = 'view-lastedit'

        for property_, icon, label in self._SORT_OPTIONS:
            button = MenuItem(icon_name=icon, text_label=label)
            button.connect('activate',
                           self.__sort_type_changed_cb,
                           property_,
                           icon)
            button.show()
            self.props.palette.menu.insert(button, -1)

    def __sort_type_changed_cb(self, widget, property_, icon_name):
        self._property = property_
        #FIXME: Implement sorting order
        self._order = gtk.SORT_ASCENDING
        self.emit('sort-property-changed')

        self.props.icon_name = icon_name

    def get_current_sort(self):
        return (self._property, self._order)
