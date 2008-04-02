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

import logging
from gettext import gettext as _

import gtk

from sugar.graphics import style
from sugar.graphics.tray import HTray
from sugar.graphics.xocolor import XoColor
from sugar.graphics.radiotoolbutton import RadioToolButton

from model import shellmodel
from view.palettes import JournalPalette, CurrentActivityPalette
from view.pulsingicon import PulsingIcon
from view.frame.frameinvoker import FrameWidgetInvoker

class ActivityButton(RadioToolButton):
    def __init__(self, home_activity, group):
        RadioToolButton.__init__(self, group=group)

        self._home_activity = home_activity

        self._icon = PulsingIcon()
        self._icon.props.base_color = home_activity.get_icon_color()
        self._icon.props.pulse_color = \
                XoColor('%s,%s' % (style.COLOR_BUTTON_GREY.get_svg(),
                                   style.COLOR_TRANSPARENT.get_svg()))
        if home_activity.get_icon_path():
            self._icon.props.file = home_activity.get_icon_path()
        else:
            self._icon.props.icon_name = 'image-missing'
        self.set_icon_widget(self._icon)
        self._icon.show()

        if self._home_activity.get_type() == "org.laptop.JournalActivity":
            palette = JournalPalette(self, self._home_activity)
        else:
            palette = CurrentActivityPalette(self, self._home_activity)
        palette.props.invoker = FrameWidgetInvoker(self)
        palette.set_group_id('frame')
        self.set_palette(palette)

        if home_activity.props.launching:
            self._icon.props.pulsing = True
            self._notify_launching_hid = home_activity.connect('notify::launching',
                    self.__notify_launching_cb)
        else:
            self._notify_launching_hid = None

    def __notify_launching_cb(self, home_activity, pspec):
        self._icon.props.pulsing = False
        home_activity.disconnect(self._notify_launching_hid)

class ActivitiesTray(HTray):
    def __init__(self):
        HTray.__init__(self)

        self._buttons = {}
        self._home_model = shellmodel.get_instance().get_home()
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

