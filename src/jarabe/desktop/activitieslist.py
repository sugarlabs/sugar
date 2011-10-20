# Copyright (C) 2008 One Laptop Per Child
# Copyright (C) 2009 Tomeu Vizoso
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

import os
import logging
from gettext import gettext as _

import gobject
import pango
import gconf
import gtk

from sugar import util
from sugar.graphics import style
from sugar.graphics.icon import Icon, CellRendererIcon
from sugar.graphics.xocolor import XoColor
from sugar.graphics.menuitem import MenuItem
from sugar.graphics.alert import Alert

from jarabe.model import bundleregistry
from jarabe.view.palettes import ActivityPalette
from jarabe.journal import misc


class ActivitiesTreeView(gtk.TreeView):
    __gtype_name__ = 'SugarActivitiesTreeView'

    __gsignals__ = {
        'erase-activated': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                            ([str])),
    }

    def __init__(self):
        gobject.GObject.__init__(self)

        self._query = ''

        self.modify_base(gtk.STATE_NORMAL, style.COLOR_WHITE.get_gdk_color())
        self.set_headers_visible(False)
        selection = self.get_selection()
        selection.set_mode(gtk.SELECTION_NONE)

        model = ListModel()
        model.set_visible_func(self.__model_visible_cb)
        self.set_model(model)

        cell_favorite = CellRendererFavorite(self)
        cell_favorite.connect('clicked', self.__favorite_clicked_cb)

        column = gtk.TreeViewColumn()
        column.pack_start(cell_favorite)
        column.set_cell_data_func(cell_favorite, self.__favorite_set_data_cb)
        self.append_column(column)

        cell_icon = CellRendererActivityIcon(self)
        cell_icon.connect('erase-activated', self.__erase_activated_cb)
        cell_icon.connect('clicked', self.__icon_clicked_cb)

        column = gtk.TreeViewColumn()
        column.pack_start(cell_icon)
        column.add_attribute(cell_icon, 'file-name', ListModel.COLUMN_ICON)
        self.append_column(column)

        cell_text = gtk.CellRendererText()
        cell_text.props.ellipsize = pango.ELLIPSIZE_MIDDLE
        cell_text.props.ellipsize_set = True

        column = gtk.TreeViewColumn()
        column.props.sizing = gtk.TREE_VIEW_COLUMN_GROW_ONLY
        column.props.expand = True
        column.set_sort_column_id(ListModel.COLUMN_TITLE)
        column.pack_start(cell_text)
        column.add_attribute(cell_text, 'markup', ListModel.COLUMN_TITLE)
        self.append_column(column)

        cell_text = gtk.CellRendererText()
        cell_text.props.xalign = 1

        column = gtk.TreeViewColumn()
        column.set_alignment(1)
        column.props.sizing = gtk.TREE_VIEW_COLUMN_GROW_ONLY
        column.props.resizable = True
        column.props.reorderable = True
        column.props.expand = True
        column.set_sort_column_id(ListModel.COLUMN_VERSION)
        column.pack_start(cell_text)
        column.add_attribute(cell_text, 'text', ListModel.COLUMN_VERSION_TEXT)
        self.append_column(column)

        cell_text = gtk.CellRendererText()
        cell_text.props.xalign = 1

        column = gtk.TreeViewColumn()
        column.set_alignment(1)
        column.props.sizing = gtk.TREE_VIEW_COLUMN_GROW_ONLY
        column.props.resizable = True
        column.props.reorderable = True
        column.props.expand = True
        column.set_sort_column_id(ListModel.COLUMN_DATE)
        column.pack_start(cell_text)
        column.add_attribute(cell_text, 'text', ListModel.COLUMN_DATE_TEXT)
        self.append_column(column)

        self.set_search_column(ListModel.COLUMN_TITLE)
        self.set_enable_search(False)

    def __erase_activated_cb(self, cell_renderer, bundle_id):
        self.emit('erase-activated', bundle_id)

    def __favorite_set_data_cb(self, column, cell, model, tree_iter):
        favorite = model[tree_iter][ListModel.COLUMN_FAVORITE]
        if favorite:
            client = gconf.client_get_default()
            color = XoColor(client.get_string('/desktop/sugar/user/color'))
            cell.props.xo_color = color
        else:
            cell.props.xo_color = None

    def __favorite_clicked_cb(self, cell, path):
        row = self.get_model()[path]
        registry = bundleregistry.get_registry()
        registry.set_bundle_favorite(row[ListModel.COLUMN_BUNDLE_ID],
                                     row[ListModel.COLUMN_VERSION],
                                     not row[ListModel.COLUMN_FAVORITE])

    def __icon_clicked_cb(self, cell, path):
        row = self.get_model()[path]

        registry = bundleregistry.get_registry()
        bundle = registry.get_bundle(row[ListModel.COLUMN_BUNDLE_ID])

        misc.launch(bundle)

    def set_filter(self, query):
        self._query = query.lower()
        self.get_model().refilter()

    def __model_visible_cb(self, model, tree_iter):
        title = model[tree_iter][ListModel.COLUMN_TITLE]
        return title is not None and title.lower().find(self._query) > -1


class ListModel(gtk.TreeModelSort):
    __gtype_name__ = 'SugarListModel'

    COLUMN_BUNDLE_ID = 0
    COLUMN_FAVORITE = 1
    COLUMN_ICON = 2
    COLUMN_TITLE = 3
    COLUMN_VERSION = 4
    COLUMN_VERSION_TEXT = 5
    COLUMN_DATE = 6
    COLUMN_DATE_TEXT = 7

    def __init__(self):
        self._model = gtk.ListStore(str, bool, str, str, str, str, int, str)
        self._model_filter = self._model.filter_new()
        gtk.TreeModelSort.__init__(self, self._model_filter)

        gobject.idle_add(self.__connect_to_bundle_registry_cb)

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
        favorite = activity_registry.is_bundle_favorite(bundle_id, version)
        for row in self._model:
            if row[ListModel.COLUMN_BUNDLE_ID] == bundle_id and \
                    row[ListModel.COLUMN_VERSION] == version:
                row[ListModel.COLUMN_FAVORITE] = favorite
                return

    def __activity_removed_cb(self, activity_registry, activity_info):
        bundle_id = activity_info.get_bundle_id()
        version = activity_info.get_activity_version()
        for row in self._model:
            if row[ListModel.COLUMN_BUNDLE_ID] == bundle_id and \
                    row[ListModel.COLUMN_VERSION] == version:
                self._model.remove(row.iter)
                return

    def _add_activity(self, activity_info):
        if activity_info.get_bundle_id() == 'org.laptop.JournalActivity':
            return

        timestamp = activity_info.get_installation_time()
        version = activity_info.get_activity_version()

        registry = bundleregistry.get_registry()
        favorite = registry.is_bundle_favorite(activity_info.get_bundle_id(),
                                               version)

        tag_list = activity_info.get_tags()
        if tag_list is None or not tag_list:
            title = '<b>%s</b>' % activity_info.get_name()
        else:
            tags = ', '.join(tag_list)
            title = '<b>%s</b>\n' \
                    '<span style="italic" weight="light">%s</span>' % \
                            (activity_info.get_name(), tags)

        self._model.append([activity_info.get_bundle_id(),
                            favorite,
                            activity_info.get_icon(),
                            title,
                            version,
                            _('Version %s') % version,
                            timestamp,
                            util.timestamp_to_elapsed_string(timestamp)])

    def set_visible_func(self, func):
        self._model_filter.set_visible_func(func)

    def refilter(self):
        self._model_filter.refilter()


class CellRendererFavorite(CellRendererIcon):
    __gtype_name__ = 'SugarCellRendererFavorite'

    def __init__(self, tree_view):
        CellRendererIcon.__init__(self, tree_view)

        self.props.width = style.GRID_CELL_SIZE
        self.props.height = style.GRID_CELL_SIZE
        self.props.size = style.SMALL_ICON_SIZE
        self.props.icon_name = 'emblem-favorite'
        self.props.mode = gtk.CELL_RENDERER_MODE_ACTIVATABLE
        client = gconf.client_get_default()
        prelit_color = XoColor(client.get_string('/desktop/sugar/user/color'))
        self.props.prelit_stroke_color = prelit_color.get_stroke_color()
        self.props.prelit_fill_color = prelit_color.get_fill_color()


class CellRendererActivityIcon(CellRendererIcon):
    __gtype_name__ = 'SugarCellRendererActivityIcon'

    __gsignals__ = {
        'erase-activated': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                            ([str])),
    }

    def __init__(self, tree_view):
        CellRendererIcon.__init__(self, tree_view)

        self.props.width = style.GRID_CELL_SIZE
        self.props.height = style.GRID_CELL_SIZE
        self.props.size = style.STANDARD_ICON_SIZE
        self.props.stroke_color = style.COLOR_BUTTON_GREY.get_svg()
        self.props.fill_color = style.COLOR_TRANSPARENT.get_svg()
        self.props.mode = gtk.CELL_RENDERER_MODE_ACTIVATABLE

        client = gconf.client_get_default()
        prelit_color = XoColor(client.get_string('/desktop/sugar/user/color'))
        self.props.prelit_stroke_color = prelit_color.get_stroke_color()
        self.props.prelit_fill_color = prelit_color.get_fill_color()

        self._tree_view = tree_view

    def create_palette(self):
        model = self._tree_view.get_model()
        row = model[self.props.palette_invoker.path]
        bundle_id = row[ListModel.COLUMN_BUNDLE_ID]

        registry = bundleregistry.get_registry()
        palette = ActivityListPalette(registry.get_bundle(bundle_id))
        palette.connect('erase-activated', self.__erase_activated_cb)
        return palette

    def __erase_activated_cb(self, palette, bundle_id):
        self.emit('erase-activated', bundle_id)


class ActivitiesList(gtk.VBox):
    __gtype_name__ = 'SugarActivitiesList'

    def __init__(self):
        logging.debug('STARTUP: Loading the activities list')

        gobject.GObject.__init__(self)

        scrolled_window = gtk.ScrolledWindow()
        scrolled_window.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        scrolled_window.set_shadow_type(gtk.SHADOW_NONE)
        scrolled_window.connect('key-press-event', self.__key_press_event_cb)
        self.pack_start(scrolled_window)
        scrolled_window.show()

        self._tree_view = ActivitiesTreeView()
        self._tree_view.connect('erase-activated', self.__erase_activated_cb)
        scrolled_window.add(self._tree_view)
        self._tree_view.show()

        self._alert = None

    def set_filter(self, query):
        self._tree_view.set_filter(query)

    def __key_press_event_cb(self, scrolled_window, event):
        keyname = gtk.gdk.keyval_name(event.keyval)

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

    def add_alert(self, alert):
        if self._alert is not None:
            self.remove_alert()
        self._alert = alert
        self.pack_start(alert, False)
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
        alert.add_button(gtk.RESPONSE_CANCEL, _('Keep'), cancel_icon)

        erase_icon = Icon(icon_name='dialog-ok')
        alert.add_button(gtk.RESPONSE_OK, _('Erase'), erase_icon)

        alert.connect('response', self.__erase_confirmation_dialog_response_cb,
                bundle_id)

        self.add_alert(alert)

    def __erase_confirmation_dialog_response_cb(self, alert, response_id,
                                                bundle_id):
        self.remove_alert()
        if response_id == gtk.RESPONSE_OK:
            registry = bundleregistry.get_registry()
            bundle = registry.get_bundle(bundle_id)
            registry.uninstall(bundle, delete_profile=True)


class ActivityListPalette(ActivityPalette):
    __gtype_name__ = 'SugarActivityListPalette'

    __gsignals__ = {
        'erase-activated': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                            ([str])),
    }

    def __init__(self, activity_info):
        ActivityPalette.__init__(self, activity_info)

        self._bundle_id = activity_info.get_bundle_id()
        self._version = activity_info.get_activity_version()

        registry = bundleregistry.get_registry()
        self._favorite = registry.is_bundle_favorite(self._bundle_id,
                                                     self._version)

        self._favorite_item = MenuItem('')
        self._favorite_icon = Icon(icon_name='emblem-favorite',
                icon_size=gtk.ICON_SIZE_MENU)
        self._favorite_item.set_image(self._favorite_icon)
        self._favorite_item.connect('activate',
                                    self.__change_favorite_activate_cb)
        self.menu.append(self._favorite_item)
        self._favorite_item.show()

        if activity_info.is_user_activity():
            self._add_erase_option(registry, activity_info)

        registry = bundleregistry.get_registry()
        self._activity_changed_sid = registry.connect('bundle_changed',
                self.__activity_changed_cb)
        self._update_favorite_item()

        self.connect('destroy', self.__destroy_cb)

    def _add_erase_option(self, registry, activity_info):
        menu_item = MenuItem(_('Erase'), 'list-remove')
        menu_item.connect('activate', self.__erase_activate_cb)
        self.menu.append(menu_item)
        menu_item.show()

        if not os.access(activity_info.get_path(), os.W_OK) or \
           registry.is_activity_protected(self._bundle_id):
            menu_item.props.sensitive = False

    def __destroy_cb(self, palette):
        registry = bundleregistry.get_registry()
        registry.disconnect(self._activity_changed_sid)

    def _update_favorite_item(self):
        label = self._favorite_item.child
        if self._favorite:
            label.set_text(_('Remove favorite'))
            xo_color = XoColor('%s,%s' % (style.COLOR_WHITE.get_svg(),
                                         style.COLOR_TRANSPARENT.get_svg()))
        else:
            label.set_text(_('Make favorite'))
            client = gconf.client_get_default()
            xo_color = XoColor(client.get_string('/desktop/sugar/user/color'))

        self._favorite_icon.props.xo_color = xo_color

    def __change_favorite_activate_cb(self, menu_item):
        registry = bundleregistry.get_registry()
        registry.set_bundle_favorite(self._bundle_id,
                                     self._version,
                                     not self._favorite)

    def __activity_changed_cb(self, activity_registry, activity_info):
        if activity_info.get_bundle_id() == self._bundle_id and \
               activity_info.get_activity_version() == self._version:
            registry = bundleregistry.get_registry()
            self._favorite = registry.is_bundle_favorite(self._bundle_id,
                                                         self._version)
            self._update_favorite_item()

    def __erase_activate_cb(self, menu_item):
        self.emit('erase-activated', self._bundle_id)
