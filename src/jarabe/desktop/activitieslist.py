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

import os
import logging
from gettext import gettext as _

import gobject
import gtk
import hippo
import gconf

from sugar import util
from sugar.graphics import style
from sugar.graphics.icon import CanvasIcon, Icon
from sugar.graphics.xocolor import XoColor
from sugar.graphics.menuitem import MenuItem
from sugar.graphics.alert import Alert
from sugar.activity import activityfactory
from sugar.activity.activityhandle import ActivityHandle

from jarabe.model import bundleregistry
from jarabe.view.palettes import ActivityPalette
from jarabe.view import launcher

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

        canvas = hippo.Canvas()
        scrolled_window.add_with_viewport(canvas)
        scrolled_window.child.set_shadow_type(gtk.SHADOW_NONE)
        canvas.show()

        self._alert = None
        self._query = ''
        self._box = hippo.CanvasBox()
        self._box.props.background_color = style.COLOR_WHITE.get_int()
        canvas.set_root(self._box)

        gobject.idle_add(self.__connect_to_bundle_registry_cb)

    def __connect_to_bundle_registry_cb(self):
        registry = bundleregistry.get_registry()
        for info in registry:
            self._add_activity(info)
        registry.connect('bundle-added', self.__activity_added_cb)
        registry.connect('bundle-removed', self.__activity_removed_cb)

    def __activity_added_cb(self, activity_registry, activity_info):
        self._add_activity(activity_info)

    def __activity_removed_cb(self, activity_registry, activity_info):
        for entry in self._box.get_children():
            if entry.get_bundle_id() == activity_info.get_bundle_id() and \
                    entry.get_version() == activity_info.get_activity_version():
                self._box.remove(entry)
                return

    def _compare_activities(self, entry_a, entry_b):
        return entry_b.get_installation_time() - entry_a.get_installation_time()

    def _add_activity(self, activity_info):
        if activity_info.get_bundle_id() == 'org.laptop.JournalActivity':
            return
        entry = ActivityEntry(activity_info)
        entry.icon.connect('erase-activated', self.__erase_activated_cb)
        self._box.insert_sorted(entry, 0, self._compare_activities)
        entry.set_visible(entry.matches(self._query))

    def __erase_activated_cb(self, activity_icon, bundle_id):
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
            registry.uninstall(bundle)

    def set_filter(self, query):
        self._query = query
        for entry in self._box.get_children():
            entry.set_visible(entry.matches(query))

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

class ActivityIcon(CanvasIcon):
    __gtype_name__ = 'SugarListActivityIcon'

    __gsignals__ = {
        'erase-activated' : (gobject.SIGNAL_RUN_FIRST,
                             gobject.TYPE_NONE, ([str]))
    }

    def __init__(self, activity_info):
        CanvasIcon.__init__(self, size=style.STANDARD_ICON_SIZE, cache=True,
                            file_name=activity_info.get_icon())
        self._activity_info = activity_info
        self._uncolor()
        self.connect('hovering-changed', self.__hovering_changed_event_cb)
        self.connect('button-release-event', self.__button_release_event_cb)

        client = gconf.client_get_default()
        self._xocolor = XoColor(client.get_string("/desktop/sugar/user/color"))

    def create_palette(self):
        palette = ActivityListPalette(self._activity_info)
        palette.connect('erase-activated', self.__erase_activated_cb)
        return palette

    def __erase_activated_cb(self, palette, bundle_id):
        self.emit('erase-activated', self._activity_info.get_bundle_id())

    def _color(self):
        self.props.xo_color = self._xocolor

    def _uncolor(self):
        self.props.stroke_color = style.COLOR_BUTTON_GREY.get_svg()
        self.props.fill_color = style.COLOR_TRANSPARENT.get_svg()

    def __hovering_changed_event_cb(self, icon, hovering):
        if hovering:
            self._color()
        else:
            self._uncolor()

    def __button_release_event_cb(self, icon, event):
        self.palette.popdown(immediate=True)
        self._uncolor()

class ActivityEntry(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'SugarActivityEntry'

    _TITLE_COL_WIDTH   = style.GRID_CELL_SIZE * 3
    _VERSION_COL_WIDTH = style.GRID_CELL_SIZE * 3
    _DATE_COL_WIDTH    = style.GRID_CELL_SIZE * 5

    def __init__(self, activity_info):
        hippo.CanvasBox.__init__(self, spacing=style.DEFAULT_SPACING,
                                 padding_top=style.DEFAULT_PADDING,
                                 padding_bottom=style.DEFAULT_PADDING,
                                 padding_left=style.DEFAULT_PADDING * 2,
                                 padding_right=style.DEFAULT_PADDING * 2,
                                 box_height=style.GRID_CELL_SIZE,
                                 orientation=hippo.ORIENTATION_HORIZONTAL)

        registry = bundleregistry.get_registry()
        registry.connect('bundle-changed', self.__activity_changed_cb)

        self._bundle = activity_info
        self._bundle_id = activity_info.get_bundle_id()
        self._version = activity_info.get_activity_version()
        self._favorite = registry.is_bundle_favorite(self._bundle_id,
                                                     self._version)
        self._title = activity_info.get_name()
        self._installation_time = activity_info.get_installation_time()

        self._favorite_icon = FavoriteIcon(self._favorite)
        self._favorite_icon.connect('notify::favorite',
                                    self.__favorite_changed_cb)
        self.append(self._favorite_icon)

        self.icon = ActivityIcon(activity_info)
        self.icon.connect('button-release-event',
                          self.__icon_button_release_event_cb)
        self.append(self.icon)

        if gtk.widget_get_default_direction() == gtk.TEXT_DIR_RTL:
            align = hippo.ALIGNMENT_END
        else:
            align = hippo.ALIGNMENT_START

        title = hippo.CanvasText(text=activity_info.get_name(),
                                 xalign=align,
                                 font_desc=style.FONT_BOLD.get_pango_desc(),
                                 box_width=ActivityEntry._TITLE_COL_WIDTH)
        self.append(title)

        version = hippo.CanvasText(text=activity_info.get_activity_version(),
                                   xalign=hippo.ALIGNMENT_END,
                                   font_desc=style.FONT_NORMAL.get_pango_desc(),
                                   box_width=ActivityEntry._VERSION_COL_WIDTH)
        self.append(version)

        expander = hippo.CanvasBox()
        self.append(expander, hippo.PACK_EXPAND)

        timestamp = activity_info.get_installation_time()
        date = hippo.CanvasText(
                text=util.timestamp_to_elapsed_string(timestamp),
                xalign=align,
                font_desc=style.FONT_NORMAL.get_pango_desc(),
                box_width=ActivityEntry._DATE_COL_WIDTH)
        self.append(date)

        if gtk.widget_get_default_direction() == gtk.TEXT_DIR_RTL:
            self.reverse()

    def __favorite_changed_cb(self, favorite_icon, pspec):
        registry = bundleregistry.get_registry()
        registry.set_bundle_favorite(self._bundle_id, self._version,
                                       favorite_icon.props.favorite)

    def __activity_changed_cb(self, activity_registry, activity_info):
        if self._bundle_id == activity_info.get_bundle_id() and \
                self._version == activity_info.get_activity_version():
            self._title = activity_info.get_name()

            registry = bundleregistry.get_registry()
            self._favorite = registry.is_bundle_favorite(self._bundle_id,
                                                         self._version)

            self._favorite_icon.props.favorite = self._favorite

    def __icon_button_release_event_cb(self, icon, event):
        activity_id = activityfactory.create_activity_id()

        client = gconf.client_get_default()
        xo_color = XoColor(client.get_string('/desktop/sugar/user/color'))

        launcher.add_launcher(activity_id,
                              self._bundle.get_icon(),
                              xo_color)

        activityfactory.create(self._bundle, ActivityHandle(activity_id))

    def get_bundle_id(self):
        return self._bundle_id

    def get_version(self):
        return self._version

    def get_installation_time(self):
        return self._installation_time

    def matches(self, query):
        if not query:
            return True
        return self._title.lower().find(query) > -1

class FavoriteIcon(CanvasIcon):
    def __init__(self, favorite):
        CanvasIcon.__init__(self, icon_name='emblem-favorite',
                            box_width=style.GRID_CELL_SIZE*3/5,
                            size=style.SMALL_ICON_SIZE)
        self._favorite = None
        self.set_favorite(favorite)
        self.connect('button-release-event', self.__release_event_cb)
        self.connect('motion-notify-event', self.__motion_notify_event_cb)

    def set_favorite(self, favorite):
        if favorite == self._favorite:
            return

        self._favorite = favorite
        if favorite:
            client = gconf.client_get_default()
            color = XoColor(client.get_string('/desktop/sugar/user/color'))
            self.props.xo_color = color
        else:
            self.props.stroke_color = style.COLOR_BUTTON_GREY.get_svg()
            self.props.fill_color = style.COLOR_WHITE.get_svg()

    def get_favorite(self):
        return self._favorite

    favorite = gobject.property(
        type=bool, default=False, getter=get_favorite, setter=set_favorite)

    def __release_event_cb(self, icon, event):
        self.props.favorite = not self.props.favorite

    def __motion_notify_event_cb(self, icon, event):
        if not self._favorite:
            if event.detail == hippo.MOTION_DETAIL_ENTER:
                icon.props.fill_color = style.COLOR_BUTTON_GREY.get_svg()
            elif event.detail == hippo.MOTION_DETAIL_LEAVE:
                icon.props.fill_color = style.COLOR_TRANSPARENT.get_svg()

class ActivityListPalette(ActivityPalette):
    __gtype_name__ = 'SugarActivityListPalette'

    __gsignals__ = {
        'erase-activated' : (gobject.SIGNAL_RUN_FIRST,
                             gobject.TYPE_NONE, ([str]))
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
        self.disconnect(self._activity_changed_sid)

    def _update_favorite_item(self):
        label = self._favorite_item.child
        if self._favorite:
            label.set_text(_('Remove favorite'))
            xo_color = XoColor('%s,%s' % (style.COLOR_WHITE.get_svg(),
                                         style.COLOR_TRANSPARENT.get_svg()))
        else:
            label.set_text(_('Make favorite'))
            client = gconf.client_get_default()
            xo_color = XoColor(client.get_string("/desktop/sugar/user/color"))

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

