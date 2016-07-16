# Copyright (C) 2008 One Laptop Per Child
# Copyright (C) 2009 Tomeu Vizoso
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

import os
import logging
from gettext import gettext as _

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk

from sugar3 import profile
from sugar3 import util
from sugar3.graphics import style
from sugar3.graphics.icon import Icon, CellRendererIcon
from sugar3.graphics.xocolor import XoColor
from sugar3.graphics.alert import Alert
from sugar3.graphics.palettemenu import PaletteMenuItem
from sugar3.graphics.scrollingdetector import ScrollingDetector
from sugar3.graphics.palettewindow import TreeViewInvoker
from sugar3.datastore import datastore

from jarabe.model import bundleregistry
from jarabe.model import desktop
from jarabe.view.palettes import ActivityPalette
from jarabe.journal import misc
from jarabe.util.normalize import normalize_string


class ActivitiesTreeView(Gtk.TreeView):
    __gtype_name__ = 'SugarActivitiesTreeView'

    __gsignals__ = {
        'erase-activated': (GObject.SignalFlags.RUN_FIRST, None,
                            ([str])),
    }

    def __init__(self):
        Gtk.TreeView.__init__(self)
        self.set_can_focus(False)

        self._query = ''

        self.set_headers_visible(False)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.TOUCH_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK)
        selection = self.get_selection()
        selection.set_mode(Gtk.SelectionMode.NONE)

        self._model = ListModel()
        self._model.set_visible_func(self.__model_visible_cb)
        self.set_model(self._model)

        self._favorite_columns = []
        for i in range(desktop.get_number_of_views()):
            self.fav_column = Gtk.TreeViewColumn()
            self.cell_favorite = CellRendererFavorite(i)
            self.cell_favorite.connect('clicked', self.__favorite_clicked_cb)
            self.fav_column.pack_start(self.cell_favorite, True)
            self.fav_column.set_cell_data_func(self.cell_favorite,
                                               self.__favorite_set_data_cb)
            self.append_column(self.fav_column)

            self._favorite_columns.append(self.fav_column)

        self.cell_icon = CellRendererActivityIcon()

        column = Gtk.TreeViewColumn()
        column.pack_start(self.cell_icon, True)
        column.add_attribute(self.cell_icon, 'file-name',
                             self._model.column_icon)
        self.append_column(column)

        self._icon_column = column

        cell_text = Gtk.CellRendererText()
        cell_text.props.ellipsize = style.ELLIPSIZE_MODE_DEFAULT
        cell_text.props.ellipsize_set = True

        column = Gtk.TreeViewColumn()
        column.props.sizing = Gtk.TreeViewColumnSizing.GROW_ONLY
        column.props.expand = True
        column.set_sort_column_id(self._model.column_title)
        column.pack_start(cell_text, True)
        column.add_attribute(cell_text, 'markup', self._model.column_title)
        self.append_column(column)

        cell_text = Gtk.CellRendererText()
        cell_text.props.xalign = 1

        self.version_column = Gtk.TreeViewColumn()
        self.version_column.set_alignment(1)
        self.version_column.props.sizing = Gtk.TreeViewColumnSizing.GROW_ONLY
        self.version_column.props.resizable = True
        self.version_column.props.reorderable = True
        self.version_column.props.expand = True
        self.version_column.set_sort_column_id(self._model.column_version)
        self.version_column.pack_start(cell_text, True)
        self.version_column.add_attribute(cell_text, 'text',
                                          self._model.column_version_text)
        self.append_column(self.version_column)

        cell_text = Gtk.CellRendererText()
        cell_text.props.xalign = 1

        self.date_column = Gtk.TreeViewColumn()
        self.date_column.set_alignment(1)
        self.date_column.props.sizing = Gtk.TreeViewColumnSizing.GROW_ONLY
        self.date_column.props.resizable = True
        self.date_column.props.reorderable = True
        self.date_column.props.expand = True
        self.date_column.set_sort_column_id(self._model.column_date)
        self.date_column.pack_start(cell_text, True)
        self.date_column.add_attribute(cell_text, 'text',
                                       self._model.column_date_text)
        self.append_column(self.date_column)

        self.set_search_column(self._model.column_title)
        self.set_enable_search(False)
        self._activity_selected = None
        self._invoker = TreeViewInvoker()
        self._invoker.attach_treeview(self)

        self.button_press_handler = None
        self.button_reslease_handler = None
        self.icon_clicked_handler = None
        self.row_activated_handler = None
        if hasattr(self.props, 'activate_on_single_click'):
            # Gtk+ 3.8 and later
            self.props.activate_on_single_click = True
            self.row_activated_handler = self.connect('row-activated',
                                                      self.__row_activated_cb)
        else:
            self.icon_clicked_handler = self.cell_icon.connect(
                'clicked', self.__icon_clicked_cb)
            self.button_press_handler = self.connect(
                'button-press-event', self.__button_press_cb)
            self.button_reslease_handler = self.connect(
                'button-release-event', self.__button_release_cb)
            self._row_activated_armed_path = None

    def __favorite_set_data_cb(self, column, cell, model, tree_iter, data):
        favorite = \
            model[tree_iter][self._model.column_favorites[cell.favorite_view]]
        if favorite:
            cell.props.xo_color = profile.get_color()
        else:
            cell.props.xo_color = None

    def __favorite_clicked_cb(self, cell, path):
        row = self.get_model()[path]
        registry = bundleregistry.get_registry()
        registry.set_bundle_favorite(
            row[self._model.column_bundle_id],
            row[self._model.column_version],
            not row[self._model.column_favorites[cell.favorite_view]],
            cell.favorite_view)

    def __icon_clicked_cb(self, cell, path):
        """
        A click on activity icon cell is to start an activity.
        """
        logging.debug('__icon_clicked_cb')
        self._start_activity(path)

    def __row_activated_cb(self, treeview, path, col):
        """
        A click on cells other than the favorite toggle is to start an
        activity.  Gtk+ 3.8 and later.
        """
        logging.debug('__row_activated_cb')
        if col is not treeview.get_column(0):
            self._start_activity(path)

    def __button_to_path(self, event, event_type):
        if event.window != self.get_bin_window() or \
           event.button != 1 or \
           event.type != event_type:
            return None

        pos = self.get_path_at_pos(int(event.x), int(event.y))
        if pos is None:
            return None

        path, column, x_, y_ = pos
        if column == self._icon_column:
            return None

        if column in self._favorite_columns:
            return None

        return path

    def __button_press_cb(self, widget, event):
        logging.debug('__button_press_cb')
        path = self.__button_to_path(event, Gdk.EventType.BUTTON_PRESS)
        if path is None:
            return

        self._row_activated_armed_path = path

    def __button_release_cb(self, widget, event):
        logging.debug('__button_release_cb')
        path = self.__button_to_path(event, Gdk.EventType.BUTTON_RELEASE)
        if path is None:
            return

        if self._row_activated_armed_path != path:
            return

        self._start_activity(path)
        self._row_activated_armed_path = None

    def _start_activity(self, path):
        model = self.get_model()
        row = model[path]

        registry = bundleregistry.get_registry()
        bundle = registry.get_bundle(row[self._model.column_bundle_id])

        misc.launch(bundle)

    def set_filter(self, query):
        """Set a new query and refilter the model, return the number
        of matching activities.

        """
        self._query = normalize_string(query.decode('utf-8'))
        self.get_model().refilter()
        matches = self.get_model().iter_n_children(None)
        return matches

    def __model_visible_cb(self, model, tree_iter, data):
        title = model[tree_iter][self._model.column_title]
        title = normalize_string(title.decode('utf-8'))
        return title is not None and title.find(self._query) > -1

    def create_palette(self, path, column):
        if column == self._icon_column:
            row = self.get_model()[path]
            bundle_id = row[self.get_model().column_bundle_id]

            registry = bundleregistry.get_registry()
            palette = ActivityListPalette(registry.get_bundle(bundle_id))
            palette.connect('erase-activated', self.__erase_activated_cb,
                            bundle_id)
            return palette

    def __erase_activated_cb(self, palette, event, bundle_id):
        self.emit('erase-activated', bundle_id)

    def get_activities_selected(self):
        activities = []
        for row in self.get_model():
            activities.append(
                {'name': row[self.get_model().column_activity_name],
                 'bundle_id': row[self.get_model().column_bundle_id]})
        return activities

    def run_activity(self, bundle_id, resume_mode):
        if not resume_mode:
            registry = bundleregistry.get_registry()
            bundle = registry.get_bundle(bundle_id)
            misc.launch(bundle)
            return

        self._activity_selected = bundle_id
        query = {'activity': bundle_id}
        properties = ['uid', 'title', 'icon-color', 'activity', 'activity_id',
                      'mime_type', 'mountpoint']
        datastore.find(query, sorting=['+timestamp'],
                       limit=1, properties=properties,
                       reply_handler=self.__get_last_activity_reply_handler_cb,
                       error_handler=self.__get_last_activity_error_handler_cb)

    def __get_last_activity_reply_handler_cb(self, entries, total_count):
        registry = bundleregistry.get_registry()
        if entries:
            misc.resume(entries[0], entries[0]['activity'])
        else:
            bundle = registry.get_bundle(self._activity_selected)
            misc.launch(bundle)

    def __get_last_activity_error_handler_cb(self, entries, total_count):
        pass

    def connect_to_scroller(self, scrolled):
        scrolled.connect('scroll-start', self._scroll_start_cb)
        scrolled.connect('scroll-end', self._scroll_end_cb)
        self.cell_icon.connect_to_scroller(scrolled)
        self.cell_favorite.connect_to_scroller(scrolled)

    def _scroll_start_cb(self, event):
        self._invoker.detach()

    def _scroll_end_cb(self, event):
        self._invoker.attach_treeview(self)


class ListModel(Gtk.TreeModelSort):
    __gtype_name__ = 'SugarListModel'

    def __init__(self):
        self.column_bundle_id = 0
        self.column_favorites = []
        for i in range(desktop.get_number_of_views()):
            self.column_favorites.append(self.column_bundle_id + i + 1)
        self.column_icon = self.column_favorites[-1] + 1
        self.column_title = self.column_icon + 1
        self.column_version = self.column_title + 1
        self.column_version_text = self.column_version + 1
        self.column_date = self.column_version_text + 1
        self.column_date_text = self.column_date + 1
        self.column_activity_name = self.column_date_text + 1

        column_types = [str, str, str, str, str, int, str, str]
        for i in range(desktop.get_number_of_views()):
            column_types.insert(1, bool)

        self._model = Gtk.ListStore()
        self._model.set_column_types(column_types)
        self._model_filter = self._model.filter_new()
        Gtk.TreeModelSort.__init__(self, model=self._model_filter)
        self.set_sort_column_id(self.column_title, Gtk.SortType.ASCENDING)

        GLib.idle_add(self.__connect_to_bundle_registry_cb)

    def __connect_to_bundle_registry_cb(self):
        registry = bundleregistry.get_registry()
        for info in registry:
            self._add_activity(info)
        registry.connect('bundle-added', self.__activity_added_cb)
        registry.connect('bundle-changed', self.__activity_changed_cb)
        registry.connect('bundle-removed', self.__activity_removed_cb)

    def __activity_added_cb(self, activity_registry, activity_info):
        self._add_activity(activity_info)

    def __activity_changed_cb(self, activity_registry, activity_info):
        bundle_id = activity_info.get_bundle_id()
        version = activity_info.get_activity_version()
        favorites = []
        for i in range(desktop.get_number_of_views()):
            favorites.append(
                activity_registry.is_bundle_favorite(bundle_id, version, i))
        for row in self._model:
            if row[self.column_bundle_id] == bundle_id and \
                    row[self.column_version] == version:
                for i in range(desktop.get_number_of_views()):
                    row[self.column_favorites[i]] = favorites[i]
                return

    def __activity_removed_cb(self, activity_registry, activity_info):
        bundle_id = activity_info.get_bundle_id()
        version = activity_info.get_activity_version()
        for row in self._model:
            if row[self.column_bundle_id] == bundle_id and \
                    row[self.column_version] == version:
                self._model.remove(row.iter)
                return

    def _add_activity(self, activity_info):
        if activity_info.get_bundle_id() == 'org.laptop.JournalActivity':
            return

        if not activity_info.get_show_launcher():
            return

        timestamp = activity_info.get_installation_time()
        version = activity_info.get_activity_version()

        registry = bundleregistry.get_registry()
        favorites = []
        for i in range(desktop.get_number_of_views()):
            favorites.append(
                registry.is_bundle_favorite(activity_info.get_bundle_id(),
                                            version,
                                            i))

        tag_list = activity_info.get_tags()
        if tag_list is None or not tag_list:
            title = '<b>%s</b>' % activity_info.get_name()
        else:
            tags = ', '.join(tag_list)
            title = '<b>%s</b>\n' \
                    '<span style="italic" weight="light">%s</span>' % \
                (activity_info.get_name(), tags)

        model_list = [activity_info.get_bundle_id()]
        for i in range(desktop.get_number_of_views()):
            model_list.append(favorites[i])
        model_list.append(activity_info.get_icon())
        model_list.append(title)
        model_list.append(version)
        model_list.append(_('Version %s') % version)
        model_list.append(int(timestamp))
        model_list.append(util.timestamp_to_elapsed_string(timestamp))
        model_list.append(activity_info.get_name())
        self._model.append(model_list)

    def set_visible_func(self, func):
        self._model_filter.set_visible_func(func)

    def refilter(self):
        self._model_filter.refilter()


class CellRendererFavorite(CellRendererIcon):
    __gtype_name__ = 'SugarCellRendererFavorite'

    def __init__(self, favorite_view):
        CellRendererIcon.__init__(self)

        self.favorite_view = favorite_view
        self.props.width = style.GRID_CELL_SIZE
        self.props.height = style.GRID_CELL_SIZE
        self.props.size = style.SMALL_ICON_SIZE
        self.props.icon_name = desktop.get_favorite_icons()[favorite_view]
        self.props.mode = Gtk.CellRendererMode.ACTIVATABLE


class CellRendererActivityIcon(CellRendererIcon):
    __gtype_name__ = 'SugarCellRendererActivityIcon'

    __gsignals__ = {
        'erase-activated': (GObject.SignalFlags.RUN_FIRST, None,
                            ([str])),
    }

    def __init__(self):
        CellRendererIcon.__init__(self)

        self.props.width = style.GRID_CELL_SIZE
        self.props.height = style.GRID_CELL_SIZE
        self.props.size = style.STANDARD_ICON_SIZE
        self.props.stroke_color = style.COLOR_BUTTON_GREY.get_svg()
        self.props.fill_color = style.COLOR_TRANSPARENT.get_svg()
        self.props.mode = Gtk.CellRendererMode.ACTIVATABLE

        prelit_color = profile.get_color()
        self.props.prelit_stroke_color = prelit_color.get_stroke_color()
        self.props.prelit_fill_color = prelit_color.get_fill_color()


class ClearMessageBox(Gtk.EventBox):

    def __init__(self, message, button_callback):
        Gtk.EventBox.__init__(self)

        self.modify_bg(Gtk.StateType.NORMAL,
                       style.COLOR_WHITE.get_gdk_color())

        alignment = Gtk.Alignment.new(0.5, 0.5, 0.1, 0.1)
        self.add(alignment)
        alignment.show()

        box = Gtk.VBox()
        alignment.add(box)
        box.show()

        icon = Icon(pixel_size=style.LARGE_ICON_SIZE,
                    icon_name='system-search',
                    stroke_color=style.COLOR_BUTTON_GREY.get_svg(),
                    fill_color=style.COLOR_TRANSPARENT.get_svg())
        box.pack_start(icon, expand=True, fill=False, padding=0)
        icon.show()

        label = Gtk.Label()
        color = style.COLOR_BUTTON_GREY.get_html()
        label.set_markup('<span weight="bold" color="%s">%s</span>' % (
            color, GLib.markup_escape_text(message)))
        box.pack_start(label, expand=True, fill=False, padding=0)
        label.show()

        button_box = Gtk.HButtonBox()
        button_box.set_layout(Gtk.ButtonBoxStyle.CENTER)
        box.pack_start(button_box, False, True, 0)
        button_box.show()

        button = Gtk.Button(label=_('Clear search'))
        button.connect('clicked', button_callback)
        button.props.image = Icon(icon_name='dialog-cancel',
                                  pixel_size=style.SMALL_ICON_SIZE)
        button_box.pack_start(button, expand=True, fill=False, padding=0)
        button.show()


class ActivitiesList(Gtk.VBox):
    __gtype_name__ = 'SugarActivitiesList'

    __gsignals__ = {
        'clear-clicked': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self):
        logging.debug('STARTUP: Loading the activities list')

        Gtk.VBox.__init__(self)

        self._scrolled_window = Gtk.ScrolledWindow()
        self._scrolled_window.set_can_focus(False)
        self._scrolled_window.set_policy(Gtk.PolicyType.NEVER,
                                         Gtk.PolicyType.AUTOMATIC)
        self._scrolled_window.set_shadow_type(Gtk.ShadowType.NONE)
        self._scrolled_window.connect('key-press-event',
                                      self.__key_press_event_cb)
        self.pack_start(self._scrolled_window, True, True, 0)
        self._scrolled_window.show()

        self._tree_view = ActivitiesTreeView()
        self._tree_view.connect('erase-activated', self.__erase_activated_cb)
        self._scrolled_window.add(self._tree_view)
        self._tree_view.show()
        scrolling_detector = ScrollingDetector(self._scrolled_window)
        self._tree_view.connect_to_scroller(scrolling_detector)

        self._alert = None
        self._clear_message_box = None

        desktop_model = desktop.get_model()
        desktop_model.connect('desktop-view-icons-changed',
                              self.__desktop_view_icons_changed_cb)

    def grab_focus(self):
        # overwrite grab focus in order to grab focus from the parent
        self._tree_view.grab_focus()

    def set_filter(self, query):
        matches = self._tree_view.set_filter(query)
        if matches == 0:
            self._show_clear_message()
        else:
            self._hide_clear_message()

    def __desktop_view_icons_changed_cb(self, model):
        self._tree_view.destroy()
        self._tree_view = ActivitiesTreeView()
        self._tree_view.connect('erase-activated', self.__erase_activated_cb)
        self._scrolled_window.add(self._tree_view)
        self._tree_view.show()

    def __key_press_event_cb(self, scrolled_window, event):
        keyname = Gdk.keyval_name(event.keyval)

        vadjustment = scrolled_window.props.vadjustment
        if keyname == 'Up':
            if vadjustment.props.value > vadjustment.props.lower:
                vadjustment.props.value -= vadjustment.props.step_increment
        elif keyname == 'Down':
            max_value = vadjustment.props.upper - vadjustment.props.page_size
            if vadjustment.props.value < max_value:
                vadjustment.props.value = min(
                    vadjustment.props.value + vadjustment.props.step_increment,
                    max_value)
        else:
            return False

        return True

    def _show_clear_message(self):
        if self._clear_message_box in self.get_children():
            return
        if self._scrolled_window in self.get_children():
            self.remove(self._scrolled_window)

        self._clear_message_box = ClearMessageBox(
            message=_('No matching activities'),
            button_callback=self.__clear_button_clicked_cb)

        self.pack_end(self._clear_message_box, True, True, 0)
        self._clear_message_box.show()

    def __clear_button_clicked_cb(self, button):
        self.emit('clear-clicked')

    def _hide_clear_message(self):
        if self._scrolled_window in self.get_children():
            return
        if self._clear_message_box in self.get_children():
            self.remove(self._clear_message_box)

        self._clear_message_box = None

        self.pack_end(self._scrolled_window, True, True, 0)
        self._scrolled_window.show()

    def add_alert(self, alert):
        if self._alert is not None:
            self.remove_alert()
        self._alert = alert
        self.pack_start(alert, False, True, 0)
        self.reorder_child(alert, 0)

    def remove_alert(self):
        self.remove(self._alert)
        self._alert = None

    def __erase_activated_cb(self, tree_view, bundle_id):
        registry = bundleregistry.get_registry()
        activity_info = registry.get_bundle(bundle_id)

        alert = Alert()
        alert.props.title = _('Confirm erase')
        alert.props.msg = \
            _('Confirm erase: Do you want to permanently erase %s?') \
            % activity_info.get_name()

        cancel_icon = Icon(icon_name='dialog-cancel')
        alert.add_button(Gtk.ResponseType.CANCEL, _('Keep'), cancel_icon)

        erase_icon = Icon(icon_name='dialog-ok')
        alert.add_button(Gtk.ResponseType.OK, _('Erase'), erase_icon)

        alert.connect('response', self.__erase_confirmation_dialog_response_cb,
                      bundle_id)

        self.add_alert(alert)

    def __erase_confirmation_dialog_response_cb(self, alert, response_id,
                                                bundle_id):
        self.remove_alert()
        if response_id == Gtk.ResponseType.OK:
            registry = bundleregistry.get_registry()
            bundle = registry.get_bundle(bundle_id)
            registry.uninstall(bundle, delete_profile=True)

    def get_activities_selected(self):
        return self._tree_view.get_activities_selected()

    def run_activity(self, bundle_id, resume_mode):
        self._tree_view.run_activity(bundle_id, resume_mode)


class ActivityListPalette(ActivityPalette):
    __gtype_name__ = 'SugarActivityListPalette'

    __gsignals__ = {
        'erase-activated': (GObject.SignalFlags.RUN_FIRST, None,
                            ([str])),
    }

    def __init__(self, activity_info):
        ActivityPalette.__init__(self, activity_info)

        self._bundle_id = activity_info.get_bundle_id()
        self._version = activity_info.get_activity_version()

        registry = bundleregistry.get_registry()

        self._favorites = []
        self._favorite_items = []
        self._favorite_icons = []

        for i in range(desktop.get_number_of_views()):
            self._favorites.append(
                registry.is_bundle_favorite(self._bundle_id, self._version, i))
            self._favorite_items.append(PaletteMenuItem())
            self._favorite_icons.append(
                Icon(icon_name=desktop.get_favorite_icons()[i],
                     pixel_size=style.SMALL_ICON_SIZE))
            self._favorite_items[i].set_image(self._favorite_icons[i])
            self._favorite_icons[i].show()
            self._favorite_items[i].connect(
                'activate', self.__change_favorite_activate_cb, i)
            self.menu_box.append_item(self._favorite_items[i])
            self._favorite_items[i].show()

        if activity_info.is_user_activity():
            self._add_erase_option(registry, activity_info)

        registry = bundleregistry.get_registry()
        self._activity_changed_sid = []
        for i in range(desktop.get_number_of_views()):
            self._activity_changed_sid.append(
                registry.connect('bundle_changed',
                                 self.__activity_changed_cb, i))
            self._update_favorite_item(i)

        self.menu_box.connect('destroy', self.__destroy_cb)

    def _add_erase_option(self, registry, activity_info):
        menu_item = PaletteMenuItem(_('Erase'), 'list-remove')
        menu_item.connect('activate', self.__erase_activate_cb)
        self.menu_box.append_item(menu_item)
        menu_item.show()

        if not os.access(activity_info.get_path(), os.W_OK) or \
           registry.is_activity_protected(self._bundle_id):
            menu_item.props.sensitive = False

    def __destroy_cb(self, palette):
        registry = bundleregistry.get_registry()
        for i in range(desktop.get_number_of_views()):
            registry.disconnect(self._activity_changed_sid[i])

    def _update_favorite_item(self, favorite_view):
        if self._favorites[favorite_view]:
            self._favorite_items[favorite_view].set_label(_('Remove favorite'))
            xo_color = XoColor('%s,%s' % (style.COLOR_WHITE.get_svg(),
                                          style.COLOR_TRANSPARENT.get_svg()))
        else:
            self._favorite_items[favorite_view].set_label(_('Make favorite'))
            xo_color = profile.get_color()

        self._favorite_icons[favorite_view].props.xo_color = xo_color

    def __change_favorite_activate_cb(self, menu_item, favorite_view):
        registry = bundleregistry.get_registry()
        registry.set_bundle_favorite(self._bundle_id,
                                     self._version,
                                     not self._favorites[favorite_view],
                                     favorite_view)

    def __activity_changed_cb(self, activity_registry, activity_info,
                              favorite_view):
        if activity_info.get_bundle_id() == self._bundle_id and \
                activity_info.get_activity_version() == self._version:
            registry = bundleregistry.get_registry()
            self._favorites[favorite_view] = registry.is_bundle_favorite(
                self._bundle_id, self._version, favorite_view)
            self._update_favorite_item(favorite_view)

    def __erase_activate_cb(self, menu_item):
        self.emit('erase-activated', self._bundle_id)
