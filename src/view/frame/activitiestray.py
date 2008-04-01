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
import logging
from gettext import gettext as _

import gtk

from sugar import env
from sugar import profile
from sugar.graphics import style
from sugar.graphics.tray import HTray
from sugar.graphics.radiotoolbutton import RadioToolButton
from sugar.graphics.icon import Icon
from sugar.graphics.palette import Palette
from sugar.graphics.menuitem import MenuItem

from view.frame.frameinvoker import FrameWidgetInvoker

class _Palette(Palette):
    def __init__(self, widget, home_activity):
        Palette.__init__(self, '', menu_after_content=True)

        self.props.invoker = FrameWidgetInvoker(widget)
        self.set_group_id('frame')

        if home_activity.props.launching:
            home_activity.connect('notify::launching', self._launching_changed_cb)
            self.set_primary_text(_('Starting...'))
        else:
            self.setup_palette()

    def _launching_changed_cb(self, home_activity, pspec):
        if not home_activity.props.launching:
            self.setup_palette()

    def setup_palette(self):
        raise NotImplementedError

class ActivityPalette(_Palette):
    def __init__(self, widget, home_activity):
        _Palette.__init__(self, widget, home_activity)
        self._home_activity = home_activity

    def setup_palette(self):
        self.set_primary_text(self._home_activity.get_title())

        menu_item = MenuItem(_('Resume'), 'activity-start')
        menu_item.connect('activate', self.__resume_activate_cb)
        self.menu.append(menu_item)
        menu_item.show()

        """ Not implemented yet
        menu_item = MenuItem(_('Share with'), 'zoom-neighborhood')
        #menu_item.connect('activate', self.__share_activate_cb)
        self.menu.append(menu_item)
        menu_item.show()

        menu_item = MenuItem(_('Keep'))
        icon = Icon(icon_name='document-save', icon_size=gtk.ICON_SIZE_MENU,
                xo_color=profile.get_color())
        menu_item.set_image(icon)
        icon.show()
        #menu_item.connect('activate', self.__keep_activate_cb)
        self.menu.append(menu_item)
        menu_item.show()
        """
        
        separator = gtk.SeparatorMenuItem()
        self.menu.append(separator)
        separator.show()

        menu_item = MenuItem(_('Stop'), 'activity-stop')
        menu_item.connect('activate', self.__stop_activate_cb)
        self.menu.append(menu_item)
        menu_item.show()

    def __resume_activate_cb(self, menu_item):
        self._home_activity.get_window().activate(1)

    def __stop_activate_cb(self, menu_item):
        self._home_activity.get_window().close(1)

class JournalPalette(_Palette):
    def __init__(self, widget, home_activity):
        _Palette.__init__(self, widget, home_activity)
        self._home_activity = home_activity
        self._progress_bar = None
        self._free_space_label = None

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
        self._home_activity.get_window().activate(1)

    def __popup_cb(self, palette):
        # TODO: we should be able to ask the datastore this info, as that's the
        # component that knows about mount points.
        stat = os.statvfs(env.get_profile_path())
        free_space = stat[statvfs.F_BSIZE] * stat[statvfs.F_BAVAIL]
        total_space = stat[statvfs.F_BSIZE] * stat[statvfs.F_BLOCKS]

        fraction = (total_space - free_space) / float(total_space)
        self._progress_bar.props.fraction = fraction
        self._free_space_label.props.label = _('%(free_space)d MB Free') % \
                {'free_space': free_space / (1024 * 1024)}

class ActivityButton(RadioToolButton):
    def __init__(self, home_activity, group):
        RadioToolButton.__init__(self, group=group)

        self._home_activity = home_activity

        icon = Icon(xo_color=home_activity.get_icon_color())
        if home_activity.get_icon_path():
            icon.props.file = home_activity.get_icon_path()
        else:
            icon.props.icon_name = 'image-missing'
        self.set_icon_widget(icon)
        icon.show()

        if self._home_activity.get_type() == "org.laptop.JournalActivity":
            palette = JournalPalette(self, self._home_activity)
        else:
            palette = ActivityPalette(self, self._home_activity)
        self.set_palette(palette)

class ActivitiesTray(HTray):
    def __init__(self, shell):
        HTray.__init__(self)

        self._buttons = {}
        self._shell = shell
        self._home_model = shell.get_model().get_home()
        self._home_model.connect('activity-added', self.__activity_added_cb)
        self._home_model.connect('activity-removed', self.__activity_removed_cb)
        self._home_model.connect('pending-activity-changed', self.__activity_changed_cb)

    def __activity_added_cb(self, home_model, home_activity):
        logging.debug('__activity_added_cb: %r' % home_activity)
        if self.get_children():
            group = self.get_children()[0]
        else:
            group = None

        button = ActivityButton(home_activity, group)
        self.add_item(button)
        self._buttons[home_activity.get_activity_id()] = button
        button.connect('toggled', self.__activity_toggled_cb, home_activity)
        button.show()

    def __activity_removed_cb(self, home_model, home_activity):
        logging.debug('__activity_removed_cb: %r' % home_activity)
        button = self._buttons[home_activity.get_activity_id()]
        self.remove_item(button)
        del self._buttons[home_activity.get_activity_id()]

    def __activity_changed_cb(self, home_model, home_activity):
        logging.debug('__activity_changed_cb: %r' % home_activity)
        button = self._buttons[home_activity.get_activity_id()]
        button.props.active = True

    def __activity_toggled_cb(self, button, home_activity):
        home_activity.get_window().activate(1)

