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
import statvfs
from gettext import gettext as _
import gconf
import logging

import gobject
import gtk

from sugar import env
from sugar.graphics.palette import Palette
from sugar.graphics.menuitem import MenuItem
from sugar.graphics.icon import Icon
from sugar.graphics import style
from sugar.graphics.xocolor import XoColor
from sugar.activity import activityfactory
from sugar.activity.activityhandle import ActivityHandle

from jarabe.model import bundleregistry
from jarabe.model import shell
from jarabe.view import launcher
from jarabe.view.viewsource import setup_view_source

class BasePalette(Palette):
    def __init__(self, home_activity):
        Palette.__init__(self)

        if home_activity.props.launching:
            home_activity.connect('notify::launching',
                                  self._launching_changed_cb)
            self.set_primary_text(_('Starting...'))
        else:
            self.setup_palette()

    def _launching_changed_cb(self, home_activity, pspec):
        if not home_activity.props.launching:
            self.setup_palette()

    def setup_palette(self):
        raise NotImplementedError

class CurrentActivityPalette(BasePalette):
    def __init__(self, home_activity):
        self._home_activity = home_activity
        BasePalette.__init__(self, home_activity)

    def setup_palette(self):
        self.set_primary_text(self._home_activity.get_title())

        menu_item = MenuItem(_('Resume'), 'activity-start')
        menu_item.connect('activate', self.__resume_activate_cb)
        self.menu.append(menu_item)
        menu_item.show()

        # TODO: share-with, keep

        menu_item = MenuItem(_('View Source'), 'view-source')
        # TODO Make this accelerator translatable
        menu_item.props.accelerator = '<Alt><Shift>v'
        menu_item.connect('activate', self.__view_source__cb)
        self.menu.append(menu_item)
        menu_item.show()

        separator = gtk.SeparatorMenuItem()
        self.menu.append(separator)
        separator.show()

        menu_item = MenuItem(_('Stop'), 'activity-stop')
        menu_item.connect('activate', self.__stop_activate_cb)
        self.menu.append(menu_item)
        menu_item.show()

    def __resume_activate_cb(self, menu_item):
        self._home_activity.get_window().activate(gtk.get_current_event_time())

    def __view_source__cb(self, menu_item):
        setup_view_source(self._home_activity)
        shell_model = shell.get_model()
        if self._home_activity is not shell_model.get_active_activity():
            self._home_activity.get_window().activate( \
                gtk.get_current_event_time())

    def __active_window_changed_cb(self, screen, previous_window=None):
        setup_view_source()
        self._screen.disconnect(self._active_window_changed_sid)

    def __stop_activate_cb(self, menu_item):
        self._home_activity.get_window().close(1)


class ActivityPalette(Palette):
    __gtype_name__ = 'SugarActivityPalette'

    __gsignals__ = {
        'erase-activated' : (gobject.SIGNAL_RUN_FIRST,
                             gobject.TYPE_NONE, ([]))
    }

    def __init__(self, activity_info):
        client = gconf.client_get_default()
        color = XoColor(client.get_string("/desktop/sugar/user/color"))
        activity_icon = Icon(file=activity_info.get_icon(),
                             xo_color=color,
                             icon_size=gtk.ICON_SIZE_LARGE_TOOLBAR)

        Palette.__init__(self, primary_text=activity_info.get_name(),
                         icon=activity_icon)

        registry = bundleregistry.get_registry()

        self._bundle = activity_info
        self._bundle_id = activity_info.get_bundle_id()
        self._version = activity_info.get_activity_version()
        self._favorite = registry.is_bundle_favorite(self._bundle_id,
                                                     self._version)

        xo_color = XoColor('%s,%s' % (style.COLOR_WHITE.get_svg(),
                                      style.COLOR_TRANSPARENT.get_svg()))
        menu_item = MenuItem(text_label=_('Start'),
                             file_name=activity_info.get_icon(),
                             xo_color=xo_color)
        menu_item.connect('activate', self.__start_activate_cb)
        self.menu.append(menu_item)
        menu_item.show()

        # TODO: start-with

        self._favorite_item = MenuItem('')
        self._favorite_icon = Icon(icon_name='emblem-favorite',
                icon_size=gtk.ICON_SIZE_MENU)
        self._favorite_item.set_image(self._favorite_icon)
        self._favorite_item.connect('activate',
                                    self.__change_favorite_activate_cb)
        self.menu.append(self._favorite_item)
        self._favorite_item.show()

        menu_item = MenuItem(_('Erase'), 'list-remove')
        menu_item.connect('activate', self.__erase_activate_cb)
        self.menu.append(menu_item)
        menu_item.show()

        if not os.access(self._bundle.get_path(), os.W_OK):
            menu_item.props.sensitive = False

        registry = bundleregistry.get_registry()
        self._activity_changed_sid = registry.connect('bundle_changed',
                self.__activity_changed_cb)
        self._update_favorite_item()

        self.connect('destroy', self.__destroy_cb)

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

    def __start_activate_cb(self, menu_item):
        self.popdown(immediate=True)

        client = gconf.client_get_default()
        xo_color = XoColor(client.get_string('/desktop/sugar/user/color'))

        activity_id = activityfactory.create_activity_id()
        launcher.add_launcher(activity_id,
                              self._bundle.get_icon(),
                              xo_color)

        handle = ActivityHandle(activity_id)
        activityfactory.create(self._bundle, handle)

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
        self.emit('erase-activated')

class JournalPalette(BasePalette):
    def __init__(self, home_activity):
        self._home_activity = home_activity
        self._progress_bar = None
        self._free_space_label = None

        BasePalette.__init__(self, home_activity)

    def setup_palette(self):
        self.set_primary_text(self._home_activity.get_title())

        vbox = gtk.VBox()
        self.set_content(vbox)
        vbox.show()

        self._progress_bar = gtk.ProgressBar()
        vbox.add(self._progress_bar)
        self._progress_bar.show()

        self._free_space_label = gtk.Label()
        self._free_space_label.set_alignment(0.5, 0.5)
        vbox.add(self._free_space_label)
        self._free_space_label.show()

        self.connect('popup', self.__popup_cb)

        menu_item = MenuItem(_('Show contents'))

        icon = Icon(file=self._home_activity.get_icon_path(),
                icon_size=gtk.ICON_SIZE_MENU,
                xo_color=self._home_activity.get_icon_color())
        menu_item.set_image(icon)
        icon.show()

        menu_item.connect('activate', self.__open_activate_cb)
        self.menu.append(menu_item)
        menu_item.show()

    def __open_activate_cb(self, menu_item):
        self._home_activity.get_window().activate(gtk.get_current_event_time())

    def __popup_cb(self, palette):
        stat = os.statvfs(env.get_profile_path())
        free_space = stat[statvfs.F_BSIZE] * stat[statvfs.F_BAVAIL]
        total_space = stat[statvfs.F_BSIZE] * stat[statvfs.F_BLOCKS]

        fraction = (total_space - free_space) / float(total_space)
        self._progress_bar.props.fraction = fraction
        self._free_space_label.props.label = _('%(free_space)d MB Free') % \
                {'free_space': free_space / (1024 * 1024)}

class VolumePalette(Palette):
    def __init__(self, mount):
        Palette.__init__(self, label=mount.get_name())
        self._mount = mount

        self.props.secondary_text = mount.get_root().get_path()

        vbox = gtk.VBox()
        self.set_content(vbox)
        vbox.show()

        self._progress_bar = gtk.ProgressBar()
        vbox.add(self._progress_bar)
        self._progress_bar.show()

        self._free_space_label = gtk.Label()
        self._free_space_label.set_alignment(0.5, 0.5)
        vbox.add(self._free_space_label)
        self._free_space_label.show()

        self.connect('popup', self.__popup_cb)

        menu_item = MenuItem(_('Unmount'))

        icon = Icon(icon_name='media-eject', icon_size=gtk.ICON_SIZE_MENU)
        menu_item.set_image(icon)
        icon.show()

        menu_item.connect('activate', self.__unmount_activate_cb)
        self.menu.append(menu_item)
        menu_item.show()

    def __unmount_activate_cb(self, menu_item):
        self._mount.unmount(self.__unmount_cb)

    def __unmount_cb(self, mount, result):
        logging.debug('__unmount_cb %r %r' % (mount, result))
        mount.unmount_finish(result)

    def __popup_cb(self, palette):
        mount_point = self._mount.get_root().get_path()
        stat = os.statvfs(mount_point)
        free_space = stat[statvfs.F_BSIZE] * stat[statvfs.F_BAVAIL]
        total_space = stat[statvfs.F_BSIZE] * stat[statvfs.F_BLOCKS]

        fraction = (total_space - free_space) / float(total_space)
        self._progress_bar.props.fraction = fraction
        self._free_space_label.props.label = _('%(free_space)d MB Free') % \
                {'free_space': free_space / (1024 * 1024)}

