# Copyright (C) 2006, Red Hat, Inc.
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

import hippo

from sugar.graphics.rollover import Rollover
from sugar.graphics.menuicon import MenuIcon
from sugar.graphics.menu import Menu
from sugar.graphics.iconcolor import IconColor
from sugar.graphics.button import Button
import sugar

class ActivityRollover(Rollover):
    ACTION_SHARE = 1
    ACTION_CLOSE = 2

    def __init__(self, activity_model):
        Rollover.__init__(self, activity_model.get_title())

        if not activity_model.get_shared():
            self.add_item(ActivityRollover.ACTION_SHARE, _('Share'),
                          'theme:stock-share-mesh')

        self.add_item(ActivityRollover.ACTION_CLOSE, _('Close'),
                      'theme:stock-close')

class ActivityButton(Button):
    def __init__(self, shell, activity_model):
        self._shell = shell
        self._activity_model = activity_model

        icon_name = self._activity_model.get_icon_name()
        icon_color = self._activity_model.get_icon_color()

        Button.__init__(self, icon_name=icon_name, color=icon_color)

    def get_rollover(self):
        rollover = ActivityRollover(self._activity_model)
        #rollover.connect('action', self._action_cb)
        return rollover
    
    def get_rollover_context(self):
        return self._shell.get_rollover_context()
    
    def _action_cb(self, menu, data):
        [action_id, label] = data

        # TODO: Wouldn't be better to share/close the activity associated with
        # this button instead of asking for the current activity?
        activity = self._shell.get_current_activity()
        if activity == None:
            logging.error('No active activity.')
            return

        if action_id == ActivityRollover.ACTION_SHARE:
            activity.share()
        elif action_id == ActivityRollover.ACTION_CLOSE:
            activity.close()

class ZoomBox(hippo.CanvasBox):
    def __init__(self, shell, menu_shell):
        hippo.CanvasBox.__init__(self, orientation=hippo.ORIENTATION_HORIZONTAL)

        self._shell = shell
        self._menu_shell = menu_shell
        self._activity_icon = None

        icon = Button(icon_name='theme:stock-zoom-mesh')
        icon.connect('activated', self._level_clicked_cb, sugar.ZOOM_MESH)
        self.append(icon)

        icon = Button(icon_name='theme:stock-zoom-friends')
        icon.connect('activated', self._level_clicked_cb, sugar.ZOOM_FRIENDS)
        self.append(icon)

        icon = Button(icon_name='theme:stock-zoom-home')
        icon.connect('activated', self._level_clicked_cb, sugar.ZOOM_HOME)
        self.append(icon)

        icon = Button(icon_name='theme:stock-zoom-activity')
        icon.connect('activated', self._level_clicked_cb, sugar.ZOOM_ACTIVITY)
        self.append(icon)

        home_model = shell.get_model().get_home()
        home_model.connect('active-activity-changed',
                           self._activity_changed_cb)
        self._set_current_activity(home_model.get_current_activity())

    def _set_current_activity(self, home_activity):
        if self._activity_icon:
            self.remove(self._activity_icon)

        if home_activity:
            icon = ActivityButton(self._shell, home_activity)
            self.append(icon)
            self._activity_icon = icon
        else:
            self._activity_icon = None

    def _activity_changed_cb(self, home_model, home_activity):
        self._set_current_activity(home_activity)

    def _level_clicked_cb(self, item, level):
        self._shell.set_zoom_level(level)
