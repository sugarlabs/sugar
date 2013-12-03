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
from gettext import ngettext
import logging
from datetime import datetime, timedelta
import os
from gi.repository import GConf
import time

from gi.repository import GObject
from gi.repository import Gtk

from sugar3.graphics.palette import Palette
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.graphics.toolcombobox import ToolComboBox
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.toggletoolbutton import ToggleToolButton
from sugar3.graphics.combobox import ComboBox
from sugar3.graphics.palettemenu import PaletteMenuBox
from sugar3.graphics.palettemenu import PaletteMenuItem
from sugar3.graphics.icon import Icon
from sugar3.graphics.xocolor import XoColor
from sugar3.graphics.alert import Alert
from sugar3.graphics import iconentry
from sugar3 import mime
from sugar3.graphics.objectchooser import FILTER_TYPE_MIME_BY_ACTIVITY
from sugar3.graphics.objectchooser import FILTER_TYPE_GENERIC_MIME
from sugar3.graphics.objectchooser import FILTER_TYPE_ACTIVITY

from jarabe.model import bundleregistry
from jarabe.journal import misc
from jarabe.journal import model
from jarabe.journal.palettes import CopyMenuBuilder
from jarabe.journal.palettes import BatchOperator
from jarabe.journal import journalwindow
from jarabe.webservice import accountsmanager


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


class MainToolbox(ToolbarBox):

    __gsignals__ = {
        'query-changed': (GObject.SignalFlags.RUN_FIRST, None,
                          ([object])),
    }

    def __init__(self):
        ToolbarBox.__init__(self)

        self._mount_point = None
        self._filter_type = None
        self._what_filter = None

        self.search_entry = iconentry.IconEntry()
        self.search_entry.set_icon_from_name(iconentry.ICON_ENTRY_PRIMARY,
                                             'entry-search')
        text = _('Search in %s') % _('Journal')
        self.search_entry.set_placeholder_text(text)
        self.search_entry.connect('activate', self._search_entry_activated_cb)
        self.search_entry.connect('changed', self._search_entry_changed_cb)
        self.search_entry.add_clear_button()
        self._autosearch_timer = None
        self._add_widget(self.search_entry, expand=True)

        self._favorite_button = ToggleToolButton('emblem-favorite')
        self._favorite_button.set_tooltip(_('Favorite entries'))
        self._favorite_button.connect('toggled',
                                      self.__favorite_button_toggled_cb)
        self.toolbar.insert(self._favorite_button, -1)
        self._favorite_button.show()

        self._what_search_combo = ComboBox()
        self._what_combo_changed_sid = self._what_search_combo.connect(
            'changed', self._combo_changed_cb)
        tool_item = ToolComboBox(self._what_search_combo)
        self.toolbar.insert(tool_item, -1)
        tool_item.show()

        self._when_search_combo = self._get_when_search_combo()
        tool_item = ToolComboBox(self._when_search_combo)
        self.toolbar.insert(tool_item, -1)
        tool_item.show()

        self._sorting_button = SortingButton()
        self.toolbar.insert(self._sorting_button, -1)
        self._sorting_button.connect('sort-property-changed',
                                     self.__sort_changed_cb)
        self._sorting_button.show()

        # TODO: enable it when the DS supports saving the buddies.
        # self._with_search_combo = self._get_with_search_combo()
        # tool_item = ToolComboBox(self._with_search_combo)
        # self.insert(tool_item, -1)
        # tool_item.show()

        self._query = self._build_query()

        self.refresh_filters()

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
        tool_item = Gtk.ToolItem()
        tool_item.set_expand(expand)

        tool_item.add(widget)
        widget.show()

        self.toolbar.insert(tool_item, -1)
        tool_item.show()

    def _build_query(self):
        query = {}

        if self._mount_point:
            query['mountpoints'] = [self._mount_point]

        if self._favorite_button.props.active:
            query['keep'] = 1

        if self._what_search_combo.props.value:
            value = self._what_search_combo.props.value
            filter_type = self._filter_type
            if self._filter_type is None:
                # for backward compatibility, try to guess the filter
                generic_type = mime.get_generic_type(value)
                if generic_type:
                    filter_type = FILTER_TYPE_GENERIC_MIME
                else:
                    filter_type = FILTER_TYPE_ACTIVITY
                logging.error('DEPRECATED: sety the filter_type parameter')

            if filter_type == FILTER_TYPE_GENERIC_MIME:
                generic_type = mime.get_generic_type(value)
                if generic_type:
                    mime_types = generic_type.mime_types
                    query['mime_type'] = mime_types
                else:
                    logging.error('filter_type="generic_mime", '
                                  'but "%s" is not a generic mime' % value)

            elif filter_type == FILTER_TYPE_ACTIVITY:
                query['activity'] = value

            elif self._filter_type == FILTER_TYPE_MIME_BY_ACTIVITY:
                registry = bundleregistry.get_registry()
                bundle = \
                    registry.get_bundle(value)
                if bundle is not None:
                    query['mime_type'] = bundle.get_mime_types()
                else:
                    logging.error('Trying to filter using activity mimetype '
                                  'but bundle id is wrong %s' % value)

        if self._when_search_combo.props.value:
            date_from, date_to = self._get_date_range()
            query['timestamp'] = {'start': date_from, 'end': date_to}

        if self.search_entry.props.text:
            text = self.search_entry.props.text.strip()
            if text:
                query['query'] = text

        property_, order = self._sorting_button.get_current_sort()

        if order == Gtk.SortType.ASCENDING:
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

    def _update_if_needed(self):
        # check if the what_search combo should be visible
        self._what_search_combo.set_visible(
            self._filter_type != FILTER_TYPE_MIME_BY_ACTIVITY)

        new_query = self._build_query()
        if self._query != new_query:
            self._query = new_query
            self.emit('query-changed', self._query)

    def _search_entry_activated_cb(self, search_entry):
        if self._autosearch_timer:
            GObject.source_remove(self._autosearch_timer)
        self._update_if_needed()

    def _search_entry_changed_cb(self, search_entry):
        if not search_entry.props.text:
            search_entry.activate()
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

    def set_mount_point(self, mount_point):
        self._mount_point = mount_point
        self._update_if_needed()

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

    def update_filters(self, mount_point, what_filter, filter_type=None):
        self._mount_point = mount_point
        self._filter_type = filter_type
        self._what_filter = what_filter
        self.set_what_filter(what_filter)
        self._update_if_needed()

    def set_filter_type(self, filter_type):
        self._filter_type = filter_type
        self._update_if_needed()

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
                        self._what_search_combo.append_item(
                            service_name,
                            activity_info.get_name(),
                            file_name=activity_info.get_icon())
                    except GObject.GError, exception:
                        logging.warning('Falling back to default icon for'
                                        ' "what" filter because %r (%r) has an'
                                        ' invalid icon: %s',
                                        activity_info.get_name(),
                                        str(service_name), exception)
                    else:
                        continue

                # fall back to generic icon
                self._what_search_combo.append_item(
                    service_name,
                    activity_info.get_name(),
                    icon_name='application-octet-stream')

        finally:
            self._what_search_combo.handler_unblock(
                self._what_combo_changed_sid)

    def __favorite_button_toggled_cb(self, favorite_button):
        self._update_if_needed()

    def clear_query(self):
        self.search_entry.props.text = ''
        if self._what_filter is None:
            self._what_search_combo.set_active(0)
        else:
            self.set_what_filter(self._what_filter)
        self._when_search_combo.set_active(0)
        self._favorite_button.props.active = False


class DetailToolbox(ToolbarBox):
    __gsignals__ = {
        'volume-error': (GObject.SignalFlags.RUN_FIRST, None,
                         ([str, str])),
    }

    def __init__(self, journalactivity):
        ToolbarBox.__init__(self)
        self._journalactivity = journalactivity
        self._metadata = None
        self._temp_file_path = None
        self._refresh = None

        self._resume = ToolButton('activity-start')
        self._resume.connect('clicked', self._resume_clicked_cb)
        self.toolbar.insert(self._resume, -1)
        self._resume.show()
        self._resume_menu = None

        client = GConf.Client.get_default()
        color = XoColor(client.get_string('/desktop/sugar/user/color'))
        self._copy = ToolButton()
        icon = Icon(icon_name='edit-copy', xo_color=color)
        self._copy.set_icon_widget(icon)
        icon.show()
        self._copy.set_tooltip(_('Copy to'))
        self._copy.connect('clicked', self._copy_clicked_cb)
        self.toolbar.insert(self._copy, -1)
        self._copy.show()

        self._duplicate = ToolButton()
        icon = Icon(icon_name='edit-duplicate', xo_color=color)
        self._duplicate.set_icon_widget(icon)
        self._duplicate.set_tooltip(_('Duplicate'))
        self._duplicate.connect('clicked', self._duplicate_clicked_cb)
        self.toolbar.insert(self._duplicate, -1)

        if accountsmanager.has_configured_accounts():
            self._refresh = ToolButton('entry-refresh')
            self._refresh.set_tooltip(_('Refresh'))
            self._refresh.connect('clicked', self._refresh_clicked_cb)
            self.toolbar.insert(self._refresh, -1)
            self._refresh.show()

        separator = Gtk.SeparatorToolItem()
        self.toolbar.insert(separator, -1)
        separator.show()

        erase_button = ToolButton('list-remove')
        erase_button.set_tooltip(_('Erase'))
        erase_button.connect('clicked', self._erase_button_clicked_cb)
        self.toolbar.insert(erase_button, -1)
        erase_button.show()

    def set_metadata(self, metadata):
        self._metadata = metadata
        self._refresh_copy_palette()
        self._refresh_duplicate_palette()
        self._refresh_refresh_palette()
        self._refresh_resume_palette()

    def _resume_clicked_cb(self, button):
        if not misc.can_resume(self._metadata):
            palette = self._resume.get_palette()
            palette.popup(immediate=True)

        misc.resume(self._metadata,
                    alert_window=journalwindow.get_journal_window())

    def _copy_clicked_cb(self, button):
        button.palette.popup(immediate=True, state=Palette.SECONDARY)

    def _refresh_clicked_cb(self, button):
        button.palette.popup(immediate=True, state=Palette.SECONDARY)

    def _duplicate_clicked_cb(self, button):
        try:
            model.copy(self._metadata, '/')
        except IOError, e:
            logging.exception('Error while copying the entry.')
            self.emit('volume-error',
                      _('Error while copying the entry. %s') % (e.strerror, ),
                      _('Error'))

    def _erase_button_clicked_cb(self, button):
        alert = Alert()
        erase_string = _('Erase')
        alert.props.title = erase_string
        alert.props.msg = _('Do you want to permanently erase \"%s\"?') \
            % self._metadata['title']
        icon = Icon(icon_name='dialog-cancel')
        alert.add_button(Gtk.ResponseType.CANCEL, _('Cancel'), icon)
        icon.show()
        ok_icon = Icon(icon_name='dialog-ok')
        alert.add_button(Gtk.ResponseType.OK, erase_string, ok_icon)
        ok_icon.show()
        alert.connect('response', self.__erase_alert_response_cb)
        journalwindow.get_journal_window().add_alert(alert)
        alert.show()

    def __erase_alert_response_cb(self, alert, response_id):
        journalwindow.get_journal_window().remove_alert(alert)
        if response_id is Gtk.ResponseType.OK:
            registry = bundleregistry.get_registry()
            bundle = misc.get_bundle(self._metadata)
            if bundle is not None and registry.is_installed(bundle):
                registry.uninstall(bundle)
            model.delete(self._metadata['uid'])

    def _resume_menu_item_activate_cb(self, menu_item, service_name):
        misc.resume(self._metadata, service_name,
                    alert_window=journalwindow.get_journal_window())

    def _refresh_copy_palette(self):
        palette = self._copy.get_palette()

        # Use the menu defined in CopyMenu
        for menu_item in palette.menu.get_children():
            palette.menu.remove(menu_item)
            menu_item.destroy()

        CopyMenuBuilder(self._journalactivity, self.__get_uid_list_cb,
                        self.__volume_error_cb, palette.menu)

    def __get_uid_list_cb(self):
        return [self._metadata['uid']]

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

    def _refresh_refresh_palette(self):
        if self._refresh is None:
            return

        color = misc.get_icon_color(self._metadata)
        self._refresh.get_icon_widget().props.xo_color = color

        palette = self._refresh.get_palette()
        for menu_item in palette.menu.get_children():
            palette.menu.remove(menu_item)

        for account in accountsmanager.get_configured_accounts():
            if hasattr(account, 'get_shared_journal_entry'):
                entry = account.get_shared_journal_entry()
                if hasattr(entry, 'get_refresh_menu'):
                    menu = entry.get_refresh_menu()
                    palette.menu.append(menu)
                    menu.set_metadata(self._metadata)

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

        if self._resume_menu is not None:
            self._resume_menu.destroy()

        self._resume_menu = PaletteMenuBox()
        palette.set_content(self._resume_menu)
        self._resume_menu.show()

        for activity_info in misc.get_activities(self._metadata):
            menu_item = PaletteMenuItem(file_name=activity_info.get_icon(),
                                        text_label=activity_info.get_name())
            menu_item.connect('activate', self._resume_menu_item_activate_cb,
                              activity_info.get_bundle_id())
            self._resume_menu.append_item(menu_item)
            menu_item.show()

        if not misc.can_resume(self._metadata):
            self._resume.set_tooltip(_('No activity to start entry'))


class SortingButton(ToolButton):
    __gtype_name__ = 'JournalSortingButton'

    __gsignals__ = {
        'sort-property-changed': (GObject.SignalFlags.RUN_FIRST,
                                  None,
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
        self._order = Gtk.SortType.ASCENDING

        self.props.tooltip = _('Sort view')
        self.props.icon_name = 'view-lastedit'

        self.props.hide_tooltip_on_click = False
        self.palette_invoker.props.toggle_palette = True

        menu_box = PaletteMenuBox()
        self.props.palette.set_content(menu_box)
        menu_box.show()

        for property_, icon, label in self._SORT_OPTIONS:
            button = PaletteMenuItem(label)
            button_icon = Icon(icon_size=Gtk.IconSize.MENU, icon_name=icon)
            button.set_image(button_icon)
            button_icon.show()
            button.connect('activate',
                           self.__sort_type_changed_cb,
                           property_,
                           icon)
            button.show()
            menu_box.append_item(button)

    def __sort_type_changed_cb(self, widget, property_, icon_name):
        self._property = property_
        # FIXME: Implement sorting order
        self._order = Gtk.SortType.ASCENDING
        self.emit('sort-property-changed')

        self.props.icon_name = icon_name

    def get_current_sort(self):
        return (self._property, self._order)


class EditToolbox(ToolbarBox):

    def __init__(self, journalactivity):
        ToolbarBox.__init__(self)
        self._journalactivity = journalactivity
        self.toolbar.add(SelectNoneButton(journalactivity))
        self.toolbar.add(SelectAllButton(journalactivity))

        self.toolbar.add(Gtk.SeparatorToolItem())

        self.batch_copy_button = BatchCopyButton(journalactivity)
        self.toolbar.add(self.batch_copy_button)
        self.toolbar.add(BatchEraseButton(journalactivity))

        self.toolbar.add(Gtk.SeparatorToolItem())

        self._multi_select_info_widget = MultiSelectEntriesInfoWidget()
        self.toolbar.add(self._multi_select_info_widget)

        self.show_all()
        self.toolbar.show_all()

    def display_selected_entries_status(self):
        info_widget = self._multi_select_info_widget
        GObject.idle_add(info_widget.display_selected_entries)

    def set_total_number_of_entries(self, total):
        self._multi_select_info_widget.set_total_number_of_entries(total)

    def set_selected_entries(self, selected):
        self._multi_select_info_widget.set_selected_entries(selected)


class SelectNoneButton(ToolButton):

    def __init__(self, journalactivity):
        ToolButton.__init__(self, 'select-none')
        self.props.tooltip = _('Deselect all')
        self._journalactivity = journalactivity

        self.connect('clicked', self.__do_deselect_all)

    def __do_deselect_all(self, widget_clicked):
        self._journalactivity.get_list_view().select_none()


class SelectAllButton(ToolButton):

    def __init__(self, journalactivity):
        ToolButton.__init__(self, 'select-all')
        self.props.tooltip = _('Select all')
        self._journalactivity = journalactivity

        self.connect('clicked', self.__do_select_all)

    def __do_select_all(self, widget_clicked):
        self._journalactivity.get_list_view().select_all()


class BatchEraseButton(ToolButton):

    def __init__(self, journalactivity):
        self._journalactivity = journalactivity
        ToolButton.__init__(self, 'edit-delete')
        self.connect('clicked', self.__button_cliecked_cb)
        self.props.tooltip = _('Erase')

    def __button_cliecked_cb(self, button):
        self._model = self._journalactivity.get_list_view().get_model()
        selected_uids = self._model.get_selected_items()
        BatchOperator(
            self._journalactivity, selected_uids, _('Erase'),
            self._get_confirmation_alert_message(len(selected_uids)),
            self._operate)

    def _get_confirmation_alert_message(self, entries_len):
        return ngettext('Do you want to erase %d entry?',
                        'Do you want to erase %d entries?',
                        entries_len) % (entries_len)

    def _operate(self, metadata):
        model.delete(metadata['uid'])
        self._model.set_selected(metadata['uid'], False)


class BatchCopyButton(ToolButton):

    def __init__(self, journalactivity):
        self._journalactivity = journalactivity
        ToolButton.__init__(self, 'edit-copy')
        self.props.tooltip = _('Copy')
        self.connect('clicked', self.__clicked_cb)

        self.menu_builder = CopyMenuBuilder(
            self._journalactivity, self.__get_uid_list_cb,
            self._journalactivity.volume_error_cb,
            self.get_palette().menu, add_clipboard_menu=False,
            add_webservices_menu=False)

    def update_mount_point(self):
        self.menu_builder.update_mount_point()

    def __clicked_cb(self, button):
        button.palette.popup(immediate=True, state=Palette.SECONDARY)

    def __get_uid_list_cb(self):
        model = self._journalactivity.get_list_view().get_model()
        return model.get_selected_items()


class MultiSelectEntriesInfoWidget(Gtk.ToolItem):

    def __init__(self):
        Gtk.ToolItem.__init__(self)

        self._box = Gtk.VBox()
        self._selected_entries = 0
        self._total = 0

        self._label = Gtk.Label()
        self._box.pack_start(self._label, True, True, 0)

        self.add(self._box)

        self.show_all()
        self._box.show_all()

    def set_total_number_of_entries(self, total):
        self._total = total

    def set_selected_entries(self, selected_entries):
        self._selected_entries = selected_entries

    def display_selected_entries(self):
        # TRANS: Do not translate %(selected)d and %(total)d.
        message = _('Selected %(selected)d of %(total)d') % {
            'selected': self._selected_entries, 'total': self._total}
        self._label.set_text(message)
        self._label.show()
