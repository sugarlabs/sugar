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

from sugar.graphics import style
from sugar.graphics.palette import Palette

from jarabe.view.buddymenu import BuddyMenu
from jarabe.view.eventicon import EventIcon


_FILTERED_ALPHA = 0.33


class BuddyIcon(EventIcon):
    def __init__(self, buddy, pixel_size=style.STANDARD_ICON_SIZE):
        EventIcon.__init__(self, icon_name='computer-xo',
                           pixel_size=pixel_size)

        self._filtered = False
        self._buddy = buddy
        self._buddy.connect('notify::present', self.__buddy_notify_present_cb)
        self._buddy.connect('notify::color', self.__buddy_notify_color_cb)

        self.connect('button-release-event', self.__button_release_event_cb)

        self.palette_invoker.cache_palette = False

        self._update_color()

    def create_palette(self):
        return BuddyMenu(self._buddy)

    def __button_release_event_cb(self, icon, event):
        self.props.palette.popup(immediate=True, state=Palette.SECONDARY)

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
        self._filtered = (self._buddy.get_nick().lower().find(query) == -1) \
                and not self._buddy.is_owner()
        self._update_color()
