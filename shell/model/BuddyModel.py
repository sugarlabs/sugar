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

from sugar.presence import presenceservice
from sugar.graphics.xocolor import XoColor
import gobject

_NOT_PRESENT_COLOR = "#888888,#BBBBBB"

class BuddyModel(gobject.GObject):
    __gsignals__ = {
        'appeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
        'disappeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
        'nick-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                         ([gobject.TYPE_PYOBJECT])),
        'color-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                         ([gobject.TYPE_PYOBJECT])),
        'icon-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                         ([])),
        'current-activity-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                                    ([gobject.TYPE_PYOBJECT]))
    }

    def __init__(self, key=None, buddy=None):
        if (key and buddy) or (not key and not buddy):
            raise RuntimeError("Must specify only _one_ of key or buddy.")

        gobject.GObject.__init__(self)

        self._ba_handler = None
        self._pc_handler = None
        self._dis_handler = None
        self._bic_handler = None
        self._cac_handler = None

        self._pservice = presenceservice.get_instance()

        self._buddy = None
        self._nick = None

        # If given just a key, try to get the buddy from the PS first
        if not buddy:
            self._key = key
            for iter_buddy in self._pservice.get_buddies():
                if iter_buddy.props.key == key:
                    buddy = iter_buddy
                    break

        # If successful, copy properties from the PS buddy object
        if buddy:
            self._update_buddy(buddy)
        else:
            # Otherwise, connect to the PS's buddy-appeared signal and
            # wait for the buddy to appear
            self._ba_handler = self._pservice.connect('buddy-appeared',
                    self._buddy_appeared_cb)
            self._key = key
            # Set color to 'inactive'/'disconnected'
            self._set_color_from_string(_NOT_PRESENT_COLOR)
            self._name = "Unknown buddy"

    def _set_color_from_string(self, color_string):
        self._color = XoColor(color_string)

    def get_key(self):
        return self._key

    def get_nick(self):
        return self._nick

    def get_color(self):
        return self._color

    def get_buddy(self):
        return self._buddy

    def is_owner(self):
        if not self._buddy:
            return False
        return self._buddy.props.owner

    def is_present(self):
        if self._buddy:
            return True
        return False

    def get_current_activity(self):
        if self._buddy:
            return self._buddy.props.current_activity
        return None

    def _update_buddy(self, buddy):
        if not buddy:
            raise ValueError("Buddy cannot be None.")

        self._buddy = buddy
        self._key = self._buddy.props.key
        self._nick = self._buddy.props.nick
        self._set_color_from_string(self._buddy.props.color)

        self._pc_handler = self._buddy.connect('property-changed', self._buddy_property_changed_cb)
        self._bic_handler = self._buddy.connect('icon-changed', self._buddy_icon_changed_cb)

    def _buddy_appeared_cb(self, pservice, buddy):
        if self._buddy or buddy.props.key != self._key:
            return

        if self._ba_handler:
            # Once we have the buddy, we no longer need to
            # monitor buddy-appeared events
            self._pservice.disconnect(self._ba_handler)
            self._ba_handler = None

        self._update_buddy(buddy)
        self.emit('appeared')

    def _buddy_property_changed_cb(self, buddy, keys):
        if not self._buddy:
            return
        if 'color' in keys:
            self._set_color_from_string(self._buddy.props.color)
            self.emit('color-changed', self.get_color())
        if 'current-activity' in keys:
            self.emit('current-activity-changed', buddy.props.current_activity)
        if 'nick' in keys:
            self._nick = self._buddy.props.nick
            self.emit('nick-changed', self.get_nick())            

    def _buddy_disappeared_cb(self, buddy):
        if buddy != self._buddy:
            return
        self._buddy.disconnect(self._pc_handler)
        self._buddy.disconnect(self._dis_handler)
        self._buddy.disconnect(self._bic_handler)
        self._buddy.disconnect(self._cac_handler)
        self._set_color_from_string(_NOT_PRESENT_COLOR)
        self.emit('disappeared')
        self._buddy = None

    def _buddy_icon_changed_cb(self, buddy):
        self.emit('icon-changed')
