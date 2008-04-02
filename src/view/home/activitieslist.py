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

import gobject
import gtk
import hippo

from sugar import profile
from sugar import activity
from sugar.graphics import style
from sugar.graphics.icon import CanvasIcon

class ActivitiesList(hippo.CanvasScrollbars):
    __gtype_name__ = 'SugarActivitiesList'

    def __init__(self, shell):
        hippo.CanvasScrollbars.__init__(self)
        self.set_policy(hippo.ORIENTATION_HORIZONTAL, hippo.SCROLLBAR_NEVER)
        
        self._shell = shell
        self._box = hippo.CanvasBox(background_color=style.COLOR_WHITE.get_int())
        self.set_root(self._box)

        registry = activity.get_registry()
        registry.get_activities_async(reply_handler=self._get_activities_cb)

        registry.connect('activity-added', self._activity_added_cb)
        registry.connect('activity-removed', self._activity_removed_cb)

    def _get_activities_cb(self, activity_list):
        for info in activity_list:
            if info.bundle_id != 'org.laptop.JournalActivity':
                self._add_activity(info)

    def _activity_added_cb(self, activity_registry, activity_info):
        self._add_activity(activity_info)

    def _activity_removed_cb(self, activity_registry, activity_info):
        """
        for item in self._tray.get_children():
            if item.get_bundle_id() == activity_info.bundle_id:
                self._tray.remove_item(item)
                return
        """
        # TODO: Implement activity removal.
        pass

    def _add_activity(self, activity_info):
        entry = ActivityEntry(self._shell, activity_info)
        #item.connect('clicked', self._activity_clicked_cb)
        #item.connect('remove_activity', self._remove_activity_cb)
        self._box.append(entry)

class ActivityEntry(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'SugarActivityEntry'

    _TITLE_COL_WIDTH   = style.GRID_CELL_SIZE * 3
    _VERSION_COL_WIDTH = style.GRID_CELL_SIZE * 1
    _DATE_COL_WIDTH    = style.GRID_CELL_SIZE * 5

    def __init__(self, shell, activity_info):
        hippo.CanvasBox.__init__(self, spacing=style.DEFAULT_SPACING,
                                 padding_top=style.DEFAULT_PADDING,
                                 padding_bottom=style.DEFAULT_PADDING,
                                 padding_left=style.DEFAULT_PADDING * 2,
                                 padding_right=style.DEFAULT_PADDING * 2,
                                 box_height=style.GRID_CELL_SIZE,
                                 orientation=hippo.ORIENTATION_HORIZONTAL)

        self._shell = shell
        self._activity_info = activity_info

        favorite_icon = FavoriteIcon(False)
        #favorite_icon.connect('button-release-event',
        #                  self._favorite_icon_button_release_event_cb)
        self.append(favorite_icon)

        icon = CanvasIcon(size=style.STANDARD_ICON_SIZE, cache=True,
                file_name=activity_info.icon,
                stroke_color=style.COLOR_BUTTON_GREY.get_svg(),
                fill_color=style.COLOR_TRANSPARENT.get_svg())
        icon.connect_after('button-release-event',
                           self.__icon_button_release_event_cb)
        self.append(icon)

        title = hippo.CanvasText(text=activity_info.name,
                                 xalign=hippo.ALIGNMENT_START,
                                 font_desc=style.FONT_BOLD.get_pango_desc(),
                                 box_width=ActivityEntry._TITLE_COL_WIDTH)
        self.append(title)

        version = hippo.CanvasText(text=activity_info.version,
                                   xalign=hippo.ALIGNMENT_END,
                                   font_desc=style.FONT_NORMAL.get_pango_desc(),
                                   box_width=ActivityEntry._VERSION_COL_WIDTH)
        self.append(version)

        expander = hippo.CanvasBox()
        self.append(expander, hippo.PACK_EXPAND)

        date = hippo.CanvasText(text='3 weeks ago',
                                xalign=hippo.ALIGNMENT_START,
                                font_desc=style.FONT_NORMAL.get_pango_desc(),
                                box_width=ActivityEntry._DATE_COL_WIDTH)
        self.append(date)

    def __icon_button_release_event_cb(self, icon, event):
        self._shell.start_activity(self._activity_info.bundle_id)

class FavoriteIcon(CanvasIcon):
    __gproperties__ = {
        'favorite' : (bool, None, None, False,
                  gobject.PARAM_READWRITE)
    }

    def __init__(self, favorite):
        CanvasIcon.__init__(self, icon_name='emblem-favorite',
                            box_width=style.GRID_CELL_SIZE*3/5,
                            size=style.SMALL_ICON_SIZE)
        self._favorite = None
        self._set_favorite(favorite)

    def _set_favorite(self, favorite):
        if favorite == self._favorite:
            return

        self._favorite = favorite
        if favorite:
            self.props.xo_color = profile.get_color()
        else:
            self.props.stroke_color = style.COLOR_BUTTON_GREY.get_svg()
            self.props.fill_color = style.COLOR_WHITE.get_svg()

    def do_set_property(self, pspec, value):
        if pspec.name == 'favorite':
            self._set_favorite(value)
        else:
            CanvasIcon.do_set_property(self, pspec, value)

    def do_get_property(self, pspec):
        if pspec.name == 'favorite':
            return self._favorite
        else:
            return CanvasIcon.do_get_property(self, pspec)

