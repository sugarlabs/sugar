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

import hippo

from sugar.graphics.canvasicon import CanvasIcon
from sugar.graphics.menuicon import MenuIcon
from sugar.graphics.menu import Menu
from sugar.graphics import style
import sugar

class ActivityMenu(Menu):
    ACTION_SHARE = 1
    ACTION_CLOSE = 2

    def __init__(self, activity_model):
        Menu.__init__(self, activity_model.get_title())

        if not activity_model.get_shared():
            self._add_mesh_action()

        self._add_close_action()

    def _add_mesh_action(self):
        icon = CanvasIcon(icon_name='stock-share-mesh')
        self.add_action(icon, ActivityMenu.ACTION_SHARE) 

    def _add_close_action(self):
        icon = CanvasIcon(icon_name='stock-close')
        self.add_action(icon, ActivityMenu.ACTION_CLOSE) 

class ActivityIcon(MenuIcon):
    def __init__(self, shell, menu_shell, activity):
        self._shell = shell
        self._activity = activity
        self._activity_model = activity.get_model()

        icon_name = self._activity_model.get_icon_name()
        icon_color = self._activity_model.get_icon_color()

        MenuIcon.__init__(self, menu_shell, icon_name=icon_name,
                          color=icon_color)

    def create_menu(self):
        menu = ActivityMenu(self._activity_model)
        menu.connect('action', self._action_cb)
        return menu

    def _action_cb(self, menu, action):
        self.popdown()

        if action == ActivityMenu.ACTION_SHARE:
            self._activity.share()
        if action == ActivityMenu.ACTION_CLOSE:
            self._activity.close()

class ZoomBox(hippo.CanvasBox):
    def __init__(self, shell, menu_shell):
        hippo.CanvasBox.__init__(self, orientation=hippo.ORIENTATION_HORIZONTAL)

        self._shell = shell
        self._menu_shell = menu_shell
        self._activity_icon = None

        icon = CanvasIcon(icon_name='stock-zoom-mesh')
        style.apply_stylesheet(icon, 'frame.ZoomIcon')
        icon.connect('activated', self._level_clicked_cb, sugar.ZOOM_MESH)
        self.append(icon)

        icon = CanvasIcon(icon_name='stock-zoom-friends')
        style.apply_stylesheet(icon, 'frame.ZoomIcon')
        icon.connect('activated', self._level_clicked_cb, sugar.ZOOM_FRIENDS)
        self.append(icon)

        icon = CanvasIcon(icon_name='stock-zoom-home')
        style.apply_stylesheet(icon, 'frame.ZoomIcon')
        icon.connect('activated', self._level_clicked_cb, sugar.ZOOM_HOME)
        self.append(icon)

        icon = CanvasIcon(icon_name='stock-zoom-activity')
        style.apply_stylesheet(icon, 'frame.ZoomIcon')
        icon.connect('activated', self._level_clicked_cb, sugar.ZOOM_ACTIVITY)
        self.append(icon)

        shell.connect('activity-changed', self._activity_changed_cb)
        self._set_current_activity(shell.get_current_activity())

    def _set_current_activity(self, activity):
        if self._activity_icon:
            self.remove(self._activity_icon)

        if activity:
            icon = ActivityIcon(self._shell, self._menu_shell, activity)
            style.apply_stylesheet(icon, 'frame.ZoomIcon')
            self.append(icon, 0)
            self._activity_icon = icon
        else:
            self._activity_icon = None

    def _activity_changed_cb(self, shell_model, activity):
        self._set_current_activity(activity)

    def _level_clicked_cb(self, item, level):
        self._shell.set_zoom_level(level)
