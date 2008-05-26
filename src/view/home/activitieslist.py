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

import gobject
import gtk
import hippo

from sugar import profile
from sugar import activity
from sugar import util
from sugar.graphics import style
from sugar.graphics.icon import CanvasIcon

import view.Shell
from view.palettes import ActivityPalette

class ActivitiesList(hippo.CanvasScrollbars):
    __gtype_name__ = 'SugarActivitiesList'

    def __init__(self):
        hippo.CanvasScrollbars.__init__(self)

        self.set_policy(hippo.ORIENTATION_HORIZONTAL, hippo.SCROLLBAR_NEVER)
        self.props.widget.connect('key-press-event', self.__key_press_event_cb)

        self._query = ''
        self._box = hippo.CanvasBox( \
                background_color=style.COLOR_WHITE.get_int())
        self.set_root(self._box)

        registry = activity.get_registry()
        registry.get_activities_async(reply_handler=self._get_activities_cb)
        registry.connect('activity-added', self.__activity_added_cb)
        registry.connect('activity-removed', self.__activity_removed_cb)

    def _get_activities_cb(self, activity_list):
        gobject.idle_add(self._add_activity_list, activity_list)

    def _add_activity_list(self, activity_list):
        info = activity_list.pop()
        if info.bundle_id != 'org.laptop.JournalActivity':
            self._add_activity(info)
        return len(activity_list) > 0

    def __activity_added_cb(self, activity_registry, activity_info):
        self._add_activity(activity_info)

    def __activity_removed_cb(self, activity_registry, activity_info):
        for entry in self.get_children():
            if entry.get_bundle_id() == activity_info.bundle_id and \
                    entry.get_version() == activity_info.version:
                self.remove(entry)
                return

    def _add_activity(self, activity_info):
        entry = ActivityEntry(activity_info)
        self._box.append(entry)
        entry.set_visible(entry.matches(self._query))

    def set_filter(self, query):
        self._query = query
        for entry in self._box.get_children():
            entry.set_visible(entry.matches(query))

    def __key_press_event_cb(self, widget, event):
        keyname = gtk.gdk.keyval_name(event.keyval)

        vadjustment = self.props.widget.props.vadjustment
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

class ActivityEntry(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'SugarActivityEntry'

    _TITLE_COL_WIDTH   = style.GRID_CELL_SIZE * 3
    _VERSION_COL_WIDTH = style.GRID_CELL_SIZE * 1
    _DATE_COL_WIDTH    = style.GRID_CELL_SIZE * 5

    def __init__(self, activity_info):
        hippo.CanvasBox.__init__(self, spacing=style.DEFAULT_SPACING,
                                 padding_top=style.DEFAULT_PADDING,
                                 padding_bottom=style.DEFAULT_PADDING,
                                 padding_left=style.DEFAULT_PADDING * 2,
                                 padding_right=style.DEFAULT_PADDING * 2,
                                 box_height=style.GRID_CELL_SIZE,
                                 orientation=hippo.ORIENTATION_HORIZONTAL)

        registry = activity.get_registry()
        registry.connect('activity-changed', self.__activity_changed_cb)

        self._bundle_id = activity_info.bundle_id
        self._version = activity_info.version
        self._favorite = activity_info.favorite
        self._title = activity_info.name

        self._favorite_icon = FavoriteIcon(self._favorite)
        self._favorite_icon.connect('notify::favorite',
                                    self.__favorite_changed_cb)
        self.append(self._favorite_icon)

        self.icon = CanvasIcon(size=style.STANDARD_ICON_SIZE, cache=True,
                file_name=activity_info.icon,
                stroke_color=style.COLOR_BUTTON_GREY.get_svg(),
                fill_color=style.COLOR_TRANSPARENT.get_svg())
        
        self.icon.set_palette(ActivityPalette(activity_info))
        self.icon.connect('hovering-changed',
                          self.__icon_hovering_changed_event_cb)
        self.icon.connect('button-release-event',
                          self.__icon_button_release_event_cb)

        self.append(self.icon)

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

        timestamp = activity_info.installation_time
        date = hippo.CanvasText(
                text=util.timestamp_to_elapsed_string(timestamp),
                xalign=hippo.ALIGNMENT_START,
                font_desc=style.FONT_NORMAL.get_pango_desc(),
                box_width=ActivityEntry._DATE_COL_WIDTH)
        self.append(date)

    def __favorite_changed_cb(self, favorite_icon, pspec):
        registry = activity.get_registry()
        registry.set_activity_favorite(self._bundle_id, self._version,
                                       favorite_icon.props.favorite)

    def __activity_changed_cb(self, activity_registry, activity_info):
        if self._bundle_id == activity_info.bundle_id and \
                self._version == activity_info.version:
            self._title = activity_info.name
            self._favorite = activity_info.favorite
            self._favorite_icon.props.favorite = self._favorite

    def __icon_hovering_changed_event_cb(self, icon, event):
        if event:
            self.icon.props.xo_color = profile.get_color()
        else:
            self.icon.props.stroke_color = style.COLOR_BUTTON_GREY.get_svg()
            self.icon.props.fill_color = style.COLOR_TRANSPARENT.get_svg()

    def __icon_button_release_event_cb(self, icon, event):
        view.Shell.get_instance().start_activity(self._bundle_id)

    def get_bundle_id(self):
        return self._bundle_id

    def get_version(self):
        return self._version

    def matches(self, query):
        if not query:
            return True
        return self._title.lower().find(query) > -1

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
        self.connect('button-release-event', self.__release_event_cb)
        self.connect('motion-notify-event', self.__motion_notify_event_cb)

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

    def __release_event_cb(self, icon, event):
        self.props.favorite = not self.props.favorite

    def __motion_notify_event_cb(self, icon, event):
        if not self._favorite:
            if event.detail == hippo.MOTION_DETAIL_ENTER:
                icon.props.fill_color = style.COLOR_BUTTON_GREY.get_svg()
            elif event.detail == hippo.MOTION_DETAIL_LEAVE:
                icon.props.fill_color = style.COLOR_TRANSPARENT.get_svg()
