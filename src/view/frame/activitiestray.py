# Copyright (C) 2006-2007 Red Hat, Inc.
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

from sugar.graphics.tray import HTray
from sugar.graphics.radiotoolbutton import RadioToolButton
from sugar.graphics.icon import Icon

class ActivityButton(RadioToolButton):
    def __init__(self, home_activity, group):
        RadioToolButton.__init__(self, group=group)

        icon = Icon(xo_color=home_activity.get_icon_color())
        if home_activity.get_icon_path():
            icon.props.file = home_activity.get_icon_path()
        else:
            icon.props.icon_name = 'image-missing'
        self.set_icon_widget(icon)
        icon.show()

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
        button.connect('toggled', self.__activity_toggled_cb,
                home_activity.get_activity_id())
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

    def __activity_toggled_cb(self, button, activity_id):
        activity_host = self._shell.get_activity(activity_id)
        if activity_host:
            activity_host.present()

