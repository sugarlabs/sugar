# Copyright (C) 2006-2007 Red Hat, Inc.
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

import gi
from gi.repository import Gio
from gi.repository import GLib

from sugar3.graphics import style
from sugar3.graphics.icon import CanvasIcon
from sugar3 import env
from sugar3.datastore import datastore

from jarabe.view.buddymenu import BuddyMenu
from jarabe.util.normalize import normalize_string

import os
import statvfs

_FILTERED_ALPHA = 0.33


class BuddyIcon(CanvasIcon):

    def __init__(self, buddy, pixel_size=style.STANDARD_ICON_SIZE):
        CanvasIcon.__init__(self, icon_name='computer-xo',
                            pixel_size=pixel_size)

        self._filtered = False
        self._buddy = buddy
        self._buddy.connect('notify::present', self.__buddy_notify_present_cb)
        self._buddy.connect('notify::color', self.__buddy_notify_color_cb)

        self.palette_invoker.props.toggle_palette = True
        self.palette_invoker.cache_palette = False

        self._update_color()

        settings = Gio.Settings('org.sugarlabs')
        variable_apr = settings.get_boolean('variable-buddy-icon')

        if variable_apr:
            self.icon_dict = {'embryo': {'normal': 'embryo-test',
                                         'disk_50': 'embryo-disk50',
                                         'disk_90': 'embryo-disk90'},
                              'teen': {'normal': 'teen',
                                       'disk_50': 'teen-disk50',
                                       'disk_90': 'teen-disk90'},
                              'adult': {'normal': 'computer-xo',
                                        'disk_50': 'adult-disk50',
                                        'disk_90': 'adult-disk90'}
                              }

            self.journal_entries = 0
            self.has_battery = None
            self.__tamagotchi_thread()
            _, self.journal_entries = datastore.find({})
            datastore.updated.connect(self.__datastore_listener_updated_cb)
            datastore.deleted.connect(self.__datastore_listener_deleted_cb)

    def __tamagotchi_thread(self):
        GLib.timeout_add(60000, self.__tamagotchi_thread)

        user_type = None
        disk_space_type = None
        _, self.total, self.used = self._get_space()

        if self.journal_entries <= 10:
            user_type = 'embryo'
        elif self.journal_entries > 10 and self.journal_entries <= 50:
            user_type = 'teen'
        elif self.journal_entries >= 50:
            user_type = 'adult'

        diskspace_50 = int(self.total / 2)
        diskspace_90 = int((90 * self.total) / 100)

        if self.used > diskspace_90:
            disk_space_type = 'disk_90'
        elif self.used > diskspace_50:
            disk_space_type = 'disk_50'
        else:
            disk_space_type = 'normal'

        self.set_icon_name(self.icon_dict[user_type][disk_space_type])
        self.__get_battery()
        self.__status_tooltip(self.has_battery)

    def __datastore_listener_updated_cb(self, **kwargs):
        self.journal_entries += 1

    def __datastore_listener_deleted_cb(self, **kwargs):
        self.journal_entries -= 1

    def __get_battery(self):
        settings = Gio.Settings('org.sugarlabs.power')
        self.has_battery = settings.get_boolean('battery-present')
        self.level = settings.get_double('battery-level')
        if self.has_battery:
            if self.level == 100:
                icon_name = 'battery-100'
            else:
                icon_name = 'battery-0' + str(int(self.level / 10)) + '0'
            self.props.badge_name = icon_name

    def __status_tooltip(self, has_battery=False):
        disk_usage = (self.used * 100) / self.total
        battery = ''
        if self.has_battery:
            battery = "\n{} Battery".format(str(self.level))
        tooltip_str = "{}% Disk space used {}".format(str(disk_usage), battery)
        self.set_tooltip_text(tooltip_str)

    def __datastore_query(self):
        _, entries = datastore.find({})
        self.journal_entries = entries

    def _get_space(self):
        stat = os.statvfs(env.get_profile_path())
        free_space = stat[statvfs.F_BSIZE] * stat[statvfs.F_BAVAIL]
        total_space = stat[statvfs.F_BSIZE] * stat[statvfs.F_BLOCKS]

        free_space = self._get_MBs(free_space)
        total_space = self._get_MBs(total_space)
        used_space = total_space - free_space

        return free_space, total_space, used_space

    def _get_MBs(self, space):
        space = space / (1024 * 1024)
        return space

    def create_palette(self):
        palette = BuddyMenu(self._buddy)
        self.connect_to_palette_pop_events(palette)
        return palette

    def __buddy_notify_present_cb(self, buddy, pspec):
        # Update the icon's color when the buddy comes and goes
        self._update_color()

    def __buddy_notify_color_cb(self, buddy, pspec):
        self._update_color()

    def _update_color(self):
        # keep the icon in the palette in sync with the view
        palette = self.get_palette()
        self.props.xo_color = self._buddy.get_color()
        if self._filtered:
            self.alpha = _FILTERED_ALPHA
            if palette is not None:
                palette.props.icon.props.stroke_color = self.props.stroke_color
                palette.props.icon.props.fill_color = self.props.fill_color
        else:
            self.alpha = 1.0
            if palette is not None:
                palette.props.icon.props.xo_color = self._buddy.get_color()

    def set_filter(self, query):
        normalized_name = normalize_string(
            self._buddy.get_nick().decode('utf-8'))
        self._filtered = (normalized_name.find(query) == -1) \
            and not self._buddy.is_owner()
        self._update_color()

    def get_positioning_data(self):
        return self._buddy.get_key()
