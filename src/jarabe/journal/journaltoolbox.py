# Copyright (C) 2007, One Laptop Per Child
# Copyright (C) 2009,14 Walter Bender
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
from gettext import ngettext
import logging
from datetime import datetime, timedelta
import os
import time

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk

from sugar3.graphics.palette import Palette
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.toggletoolbutton import ToggleToolButton
from sugar3.graphics.palette import ToolInvoker
from sugar3.graphics.palettemenu import PaletteMenuBox
from sugar3.graphics.palettemenu import PaletteMenuItem
from sugar3.graphics.palettemenu import PaletteMenuItemSeparator
from sugar3.graphics.icon import Icon, EventIcon
from sugar3.graphics.alert import Alert
from sugar3.graphics.xocolor import XoColor
from sugar3.graphics import iconentry
from sugar3.graphics import style
from sugar3 import mime
from sugar3 import profile
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

_WHITE = style.COLOR_WHITE.get_html()
_LABEL_MAX_WIDTH = 18
_MAXIMUM_PALETTE_COLUMNS = 4


class MainToolbox(ToolbarBox):

    query_changed_signal = GObject.Signal('query-changed',
                                          arg_types=([object]))

    def __init__(self, default_what_filter=None, default_filter_type=None):
        ToolbarBox.__init__(self)
        self._mount_point = None
        self._filter_type = default_filter_type
        self._what_filter = default_what_filter
        self._when_filter = None

        self._default_what_filter = default_what_filter
        self._default_filter_type = default_filter_type

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

        self._proj_list_button = ToggleToolButton('project-box')
        self._proj_list_button.set_tooltip(_('Projects'))
        self._proj_list_button.connect('toggled',
                                       self._proj_list_button_clicked_cb)
        self.toolbar.insert(self._proj_list_button, -1)
        self._proj_list_button.show()

        if not self._proj_list_button.props.active:
            self._what_widget_contents = None
            self._what_widget = Gtk.ToolItem()
            self._what_search_button = FilterToolItem(
                'view-type', _('Anything'), self._what_widget)
            self._what_widget.show()
            self.toolbar.insert(self._what_search_button, -1)
            self._what_search_button.show()

        self._when_search_button = FilterToolItem(
            'view-created', _('Anytime'), self._get_when_search_items())
        self.toolbar.insert(self._when_search_button, -1)
        self._when_search_button.show()

        self._sorting_button = SortingButton()
        self.toolbar.insert(self._sorting_button, -1)
        self._sorting_button.connect('sort-property-changed',
                                     self.__sort_changed_cb)
        self._sorting_button.show()

        '''
        # TODO: enable it when the DS supports saving the buddies.
        self._with_widget = Gtk.ToolItem()
        self._with_search_button = FilterToolItem(
            'view-who', _('Anyone'), self._with_widget)
        self._with_widget.show()
        self.toolbar.insert(self._with_search_button, -1)
        self._with_search_button.show()
        self._get_with_search_items()
        '''

        self._query = self._build_query()

        self.refresh_filters()

        self.connect('size_allocate', self.__size_allocate_cb)

    def __size_allocate_cb(self, widget, allocation):
        GObject.idle_add(self._update_buttons, allocation.width)

    def _update_buttons(self, toolbar_width):
        # Show the label next to the button icon if there is room on
        # the toolbar.
        important = toolbar_width > 13 * style.GRID_CELL_SIZE

        if not important:
            self.search_entry.set_size_request(
                toolbar_width - style.GRID_CELL_SIZE * 7, 0)

        self._what_search_button.set_is_important(important)
        self._when_search_button.set_is_important(important)
        # self._with_search_button.set_is_important(important)

        return False

    def _get_when_search_items(self):
        when_list = []
        when_list.append({'label': _('Anytime'),
                          'callback': self._when_palette_cb,
                          'id': _ACTION_ANYTIME})
        when_list.append({'separator': True})
        when_list.append({'label': _('Today'),
                          'callback': self._when_palette_cb,
                          'id': _ACTION_TODAY})
        when_list.append({'label': _('Since yesterday'),
                          'callback': self._when_palette_cb,
                          'id': _ACTION_SINCE_YESTERDAY})
        when_list.append({'label': _('Past week'),
                          'callback': self._when_palette_cb,
                          'id': _ACTION_PAST_WEEK})
        when_list.append({'label': _('Past month'),
                          'callback': self._when_palette_cb,
                          'id': _ACTION_PAST_MONTH})
        when_list.append({'label': _('Past year'),
                          'callback': self._when_palette_cb,
                          'id': _ACTION_PAST_YEAR})

        return set_palette_list(when_list)

    '''
    def _get_with_search_items(self):
        with_list = []
        with_list.append({'label':_('Anyone'),
                          'callback': self._with_palette_cb,
                          'id': _ACTION_EVERYBODY})
        with_list.append({'separator': True})
        with_list.append({'label':_('My friends'),
                          'callback': self._with_palette_cb,
                          'id': _ACTION_MY_FRIENDS})
        with_list.append({'label':_('My class'),
                          'callback': self._with_palette_cb,
                          'id': _ACTION_MY_CLASS})
        with_list.append({'separator': True})
        # TODO: Ask the model for buddies.
        for i, buddy in enumerate(model.get_buddies()):
            nick, color = buddy
            with_list.append({'label': nick,
                              'callback': self._with_palette_cb,
                              'icon': 'computer-xo',
                              'xocolors': XOColor(color),
                              'id': i + _ACTION_MY_CLASS + 1})

        widget = set_palette_list(with_list)
        self._with_widget.add(widget)
        widget.show()
    '''

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

        if self._proj_list_button.props.active:
            query['activity'] = 'org.sugarlabs.Project'

        elif self._what_filter:
            filter_type = self._filter_type
            value = self._what_filter

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

        if self._when_filter:
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

        if self._when_filter == _ACTION_TODAY:
            date_range = (today_start, right_now)
        elif self._when_filter == _ACTION_SINCE_YESTERDAY:
            date_range = (today_start - timedelta(1), right_now)
        elif self._when_filter == _ACTION_PAST_WEEK:
            date_range = (today_start - timedelta(7), right_now)
        elif self._when_filter == _ACTION_PAST_MONTH:
            date_range = (today_start - timedelta(30), right_now)
        elif self._when_filter == _ACTION_PAST_YEAR:
            date_range = (today_start - timedelta(356), right_now)

        return (time.mktime(date_range[0].timetuple()),
                time.mktime(date_range[1].timetuple()))

    def __sort_changed_cb(self, button):
        self._update_if_needed()

    def _update_if_needed(self):
        new_query = self._build_query()
        if self._query != new_query:
            self._query = new_query
            self.query_changed_signal.emit(self._query)

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
        for item in self._what_list:
            if 'id' in item and item['id'] == what_filter:
                self._what_search_button.set_widget_label(item['label'])

                if item['id'] == 0:
                    self._what_search_button.set_widget_icon(
                        icon_name='view-type')
                elif 'icon' in item:
                    self._what_search_button.set_widget_icon(
                        icon_name=item['icon'])
                    self._filter_type = FILTER_TYPE_GENERIC_MIME
                elif 'file' in item:
                    self._what_search_button.set_widget_icon(
                        file_name=item['file'])
                    if self._default_filter_type is not None:
                        self._filter_type = self._default_filter_type
                    else:
                        self._filter_type = FILTER_TYPE_ACTIVITY
                self._what_filter = what_filter
                break

    def update_filters(self, mount_point, what_filter, filter_type=None):
        self._mount_point = mount_point
        self._filter_type = filter_type
        self._what_filter = what_filter
        self.set_what_filter(what_filter)
        self._update_if_needed()

    def set_filter_type(self, filter_type):
        self._filter_type = filter_type
        self._update_if_needed()

    def _what_palette_cb(self, widget, event, item):
        self._what_search_button.set_widget_label(item['label'])

        if item['id'] == 0:
            self._what_search_button.set_widget_icon(icon_name='view-type')
        elif 'icon' in item:
            self._what_search_button.set_widget_icon(icon_name=item['icon'])
            self._filter_type = FILTER_TYPE_GENERIC_MIME
        elif 'file' in item:
            self._what_search_button.set_widget_icon(file_name=item['file'])
            if self._default_filter_type is not None:
                self._filter_type = self._default_filter_type
            else:
                self._filter_type = FILTER_TYPE_ACTIVITY

        self._what_filter = item['id']

        new_query = self._build_query()
        if self._query != new_query:
            self._query = new_query
            self.query_changed_signal.emit(self._query)

    def _when_palette_cb(self, widget, event, item):
        self._when_search_button.set_widget_label(item['label'])

        self._when_filter = item['id']

        new_query = self._build_query()
        if self._query != new_query:
            self._query = new_query
            self.query_changed_signal.emit(self._query)

    def refresh_filters(self):
        # refresh_what_filters
        self._what_list = []
        what_list_activities = []

        try:
            # TRANS: Item on a palette that filters by entry type.
            self._what_list.append({'label': _('Anything'),
                                    'icon': 'application-octet-stream',
                                    'callback': self._what_palette_cb,
                                    'id': _ACTION_ANYTHING})

            registry = bundleregistry.get_registry()
            appended_separator = False

            types = mime.get_all_generic_types()
            for generic_type in types:
                if not appended_separator:
                    self._what_list.append({'separator': True})
                    appended_separator = True
                self._what_list.append({'label': generic_type.name,
                                        'icon': generic_type.icon,
                                        'callback': self._what_palette_cb,
                                        'id': generic_type.type_id})

            self._what_list.append({'separator': True})

            for bundle_id in model.get_unique_values('activity'):
                activity_info = registry.get_bundle(bundle_id)
                if activity_info is None:
                    continue

                # try activity-provided icon
                if os.path.exists(activity_info.get_icon()):
                    try:
                        what_list_activities.append(
                            {'label': activity_info.get_name(),
                             'file': activity_info.get_icon(),
                             'callback': self._what_palette_cb,
                             'id': bundle_id})
                    except GObject.GError as exception:
                        # fall back to generic icon
                        logging.warning('Falling back to default icon for'
                                        ' "what" filter because %r (%r) has an'
                                        ' invalid icon: %s',
                                        activity_info.get_name(),
                                        str(bundle_id), exception)
                        what_list_activities.append(
                            {'label': activity_info.get_name(),
                             'icon': 'application-octet-stream',
                             'callback': self._what_palette_cb,
                             'id': bundle_id})
        finally:
            def _cmp(a, b):
                if a['label'] < b['label']:
                    return -1
                else:
                    return 1

            for item in sorted(what_list_activities, _cmp):
                self._what_list.append(item)

            if self._what_widget_contents is not None:
                self._what_widget.remove(self._what_widget_contents)
            self._what_widget_contents = set_palette_list(self._what_list)
            self._what_widget.add(self._what_widget_contents)
            self._what_widget_contents.show()

    def _proj_list_button_clicked_cb(self, proj_list_button):
        if self._proj_list_button.props.active:
            self._what_widget.hide()
            self._what_search_button.hide()
        else:
            self._what_widget.show()
            self._what_search_button.show()
        self._update_if_needed()

    def __favorite_button_toggled_cb(self, favorite_button):
        self._update_if_needed()

    def is_filter_changed(self):
        return not (self._filter_type == self._default_filter_type and
                    self._what_filter == self._default_what_filter and
                    self._when_filter is None and
                    self._favorite_button.props.active is False and
                    self.search_entry.props.text == '')

    def clear_query(self):
        self.search_entry.props.text = ''
        self._filter_type = self._default_filter_type

        self._what_search_button.set_widget_icon(icon_name='view-type')
        self._what_search_button.set_widget_label(_('Anything'))
        self.set_what_filter(self._default_what_filter)

        self._when_search_button.set_widget_icon(icon_name='view-created')
        self._when_search_button.set_widget_label(_('Anytime'))
        self._when_filter = None

        '''
        self._with_search_button.set_widget_icon(icon_name='view-who')
        self._with_search_button.set_widget_label(_('Anyone'))
        self._with_filter = None
        '''

        self._favorite_button.props.active = False

        if self._proj_list_button.props.active:
            self._what_widget.show()
            self._what_search_button.show()
            self._proj_list_button.props.active = False

        self._update_if_needed()


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

        color = profile.get_color()
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
        button.palette.popup(immediate=True)

    def _refresh_clicked_cb(self, button):
        button.palette.popup(immediate=True)

    def _duplicate_clicked_cb(self, button):
        try:
            model.copy(self._metadata, '/')
        except IOError as e:
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

        sort_options = [
            ('timestamp', 'view-lastedit', _('Sort by date modified')),
            ('creation_time', 'view-created', _('Sort by date created')),
            ('filesize', 'view-size', _('Sort by size')),
        ]

        for property_, icon, label in sort_options:
            button = PaletteMenuItem(label)
            button_icon = Icon(pixel_size=style.SMALL_ICON_SIZE,
                               icon_name=icon)
            button.set_image(button_icon)
            button_icon.show()
            button.connect('activate',
                           self.__sort_type_changed_cb,
                           property_,
                           icon)
            button.show()
            menu_box.append_item(button)

    def __sort_type_changed_cb(self, widget, property_, icon_name):
        if self._property == property_:
            if self._order == Gtk.SortType.ASCENDING:
                self._order = Gtk.SortType.DESCENDING
            else:
                self._order = Gtk.SortType.ASCENDING
        else:
            self._order = Gtk.SortType.ASCENDING

        self._property = property_
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
        self._menu_builder = None

    def _refresh_menu_options(self):
        if self._menu_builder is not None:
            return
        self._menu_builder = CopyMenuBuilder(
            self._journalactivity, self.__get_uid_list_cb,
            self._journalactivity.volume_error_cb,
            self.get_palette().menu, add_clipboard_menu=False,
            add_webservices_menu=False)

    def update_mount_point(self):
        if self._menu_builder is not None:
            self._menu_builder.update_mount_point()

    def __clicked_cb(self, button):
        self._refresh_menu_options()
        button.palette.popup(immediate=True)

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


class FilterToolItem(Gtk.ToolButton):

    __gsignals__ = {
        'changed': (GObject.SignalFlags.RUN_LAST, None, ([])), }

    def __init__(self, default_icon, default_label, palette_content):
        self._palette_invoker = ToolInvoker()
        Gtk.ToolButton.__init__(self)
        self._label = default_label

        self.set_is_important(False)
        self.set_size_request(style.GRID_CELL_SIZE, -1)

        self._label_widget = Gtk.Label()
        self._label_widget.set_alignment(0.0, 0.5)
        self._label_widget.set_ellipsize(style.ELLIPSIZE_MODE_DEFAULT)
        self._label_widget.set_max_width_chars(_LABEL_MAX_WIDTH)
        self._label_widget.set_use_markup(True)
        self._label_widget.set_markup(default_label)
        self.set_label_widget(self._label_widget)
        self._label_widget.show()

        self.set_widget_icon(icon_name=default_icon)

        self._hide_tooltip_on_click = True
        self._palette_invoker.attach_tool(self)
        self._palette_invoker.props.toggle_palette = True
        self._palette_invoker.props.lock_palette = True

        self.palette = Palette(_('Select filter'))
        self.palette.set_invoker(self._palette_invoker)

        self.props.palette.set_content(palette_content)

    def set_widget_icon(self, icon_name=None, file_name=None):
        if file_name is not None:
            icon = Icon(file=file_name,
                        pixel_size=style.SMALL_ICON_SIZE,
                        xo_color=XoColor('white'))
        else:
            icon = Icon(icon_name=icon_name,
                        pixel_size=style.SMALL_ICON_SIZE,
                        xo_color=XoColor('white'))
        self.set_icon_widget(icon)
        icon.show()

    def set_widget_label(self, label=None):
        # FIXME: Ellipsis is not working on these labels.
        if label is None:
            label = self._label
        if len(label) > _LABEL_MAX_WIDTH:
            label = label[0:7] + '...' + label[-7:]
        self._label_widget.set_markup(label)
        self._label = label

    def __destroy_cb(self, icon):
        if self._palette_invoker is not None:
            self._palette_invoker.detach()

    def create_palette(self):
        return None

    def get_palette(self):
        return self._palette_invoker.palette

    def set_palette(self, palette):
        self._palette_invoker.palette = palette

    palette = GObject.property(
        type=object, setter=set_palette, getter=get_palette)

    def get_palette_invoker(self):
        return self._palette_invoker

    def set_palette_invoker(self, palette_invoker):
        self._palette_invoker.detach()
        self._palette_invoker = palette_invoker

    palette_invoker = GObject.property(
        type=object, setter=set_palette_invoker, getter=get_palette_invoker)

    def do_draw(self, cr):
        if self.palette and self.palette.is_up():
            allocation = self.get_allocation()
            # draw a black background, has been done by the engine before
            cr.set_source_rgb(0, 0, 0)
            cr.rectangle(0, 0, allocation.width, allocation.height)
            cr.paint()

        Gtk.ToolButton.do_draw(self, cr)

        if self.palette and self.palette.is_up():
            invoker = self.palette.props.invoker
            invoker.draw_rectangle(cr, self.palette)

        return False
if hasattr(FilterToolItem, 'set_css_name'):
    FilterToolItem.set_css_name('filtertoolbutton')


def set_palette_list(palette_list):
    if 'icon' in palette_list[0]:
        _menu_item = PaletteMenuItem(icon_name=palette_list[0]['icon'],
                                     text_label=palette_list[0]['label'])
    else:
        _menu_item = PaletteMenuItem(text_label=palette_list[0]['label'])
    req2 = _menu_item.get_preferred_size()[1]
    menuitem_width = req2.width
    menuitem_height = req2.height

    palette_width = Gdk.Screen.width() - style.GRID_CELL_SIZE
    palette_height = Gdk.Screen.height() - style.GRID_CELL_SIZE * 3

    nx = min(_MAXIMUM_PALETTE_COLUMNS, int(palette_width / menuitem_width))
    ny = min(int(palette_height / menuitem_height), len(palette_list) + 1)
    if ny >= len(palette_list):
        nx = 1
        ny = len(palette_list)

    grid = Gtk.Grid()
    grid.set_row_spacing(style.DEFAULT_PADDING)
    grid.set_column_spacing(0)
    grid.set_border_width(0)
    grid.show()

    x = 0
    y = 0
    xo_color = XoColor('white')

    for item in palette_list:
        if 'separator' in item:
            menu_item = PaletteMenuItemSeparator()
        elif 'icon' in item:
            menu_item = PaletteMenuItem(icon_name=item['icon'],
                                        text_label=item['label'],
                                        xo_color=xo_color)
        elif 'file' in item:
            menu_item = PaletteMenuItem(file_name=item['file'],
                                        text_label=item['label'],
                                        xo_color=xo_color)
        else:
            menu_item = PaletteMenuItem()
            menu_item.set_label(item['label'])

        menu_item.set_size_request(style.GRID_CELL_SIZE * 3, -1)

        if 'separator' in item:
            y += 1
            grid.attach(menu_item, 0, y, nx, 1)
            x = 0
            y += 1
        else:
            menu_item.connect('button-release-event', item['callback'], item)
            grid.attach(menu_item, x, y, 1, 1)
            x += 1
            if x == nx:
                x = 0
                y += 1

        menu_item.show()

    if palette_height < (y * menuitem_height + style.GRID_CELL_SIZE):
        # if the grid is bigger than the palette, put in a scrolledwindow
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER,
                                   Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_size_request(nx * menuitem_width,
                                         (ny + 1) * menuitem_height)
        scrolled_window.add_with_viewport(grid)
        return scrolled_window
    else:
        return grid


class AddNewBar(Gtk.Box):

    activate = GObject.Signal('activate', arg_types=[str])

    def __init__(self, placeholder=None):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.HORIZONTAL)

        self._button = EventIcon(icon_name='list-add')
        self._button.connect('button-release-event',
                             self.__button_release_event_cb)
        self._button.fill_color = style.COLOR_TOOLBAR_GREY.get_svg()
        self._button.set_tooltip(_('Add New'))
        self.pack_start(self._button, False, True, 0)
        self._button.show()

        self._entry = iconentry.IconEntry()
        self._entry.connect('key-press-event', self.__key_press_cb)
        if placeholder is None:
            placeholder = _('Add new entry')
        self._entry.set_placeholder_text(placeholder)
        self._entry.add_clear_button()
        self.pack_start(self._entry, True, True, 0)
        self._entry.show()

    def get_entry(self):
        return self._entry

    def get_button(self):
        return self._button

    def __key_press_cb(self, window, event):
        if event.keyval == Gdk.KEY_Return:
            return self._maybe_activate()

    def __button_release_event_cb(self, button, event):
        self._maybe_activate()

    def _maybe_activate(self):
        if self._entry.props.text:
            self.activate.emit(self._entry.props.text)
            self._entry.props.text = ''
            return True
