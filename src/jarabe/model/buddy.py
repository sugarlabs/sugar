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

from sugar.presence import presenceservice
from sugar.graphics.xocolor import XoColor
import gobject

_NOT_PRESENT_COLOR = "#d5d5d5,#FFFFFF"

class BaseBuddyModel(gobject.GObject):
    __gtype_name__ = 'SugarBaseBuddyModel'

    def __init__(self, **kwargs):
        self._key = None
        self._nick = None
        self._color = None
        self._tags = None
        self._present = False

        gobject.GObject.__init__(self, **kwargs)

    def _set_color_from_string(self, color_string):
        self._color = XoColor(color_string)

    def is_present(self):
        return self._present

    def set_present(self, present):
        self._present = present

    present = gobject.property(type=bool, default=False, getter=is_present,
                               setter=set_present)

    def get_nick(self):
        return self._nick

    def set_nick(self, nick):
        self._nick = nick

    nick = gobject.property(type=object, getter=get_nick, setter=set_nick)

    def get_key(self):
        return self._key

    key = gobject.property(type=object, getter=get_key)

    def get_color(self):
        return self._color

    color = gobject.property(type=object, getter=get_color)

    def get_tags(self):
        return self._tags

    tags = gobject.property(type=object, getter=get_tags)

    def get_current_activity(self):
        raise NotImplementedError

    current_activity = gobject.property(type=object,
                                        getter=get_current_activity)

    def is_owner(self):
        raise NotImplementedError

    def get_buddy(self):
        raise NotImplementedError


class OwnerBuddyModel(BaseBuddyModel):
    __gtype_name__ = 'SugarOwnerBuddyModel'
    def __init__(self):
        BaseBuddyModel.__init__(self)
        self.props.present = True
        self.props.nick = 'XXXXXXXXXXXXXX'
        self.props.color = ''

    def is_owner(self):
        return True

    def get_buddy(self):
        return None


class BuddyModel(BaseBuddyModel):
    __gtype_name__ = 'SugarBuddyModel'
    def __init__(self, key=None, buddy=None, nick=None):
        if (key and buddy) or (not key and not buddy):
            raise RuntimeError("Must specify only _one_ of key or buddy.")

        BaseBuddyModel.__init__(self, nick=nick, key=key)
        
        self._pservice = presenceservice.get_instance()

        self._buddy = None
        self._ba_handler = None
        self._pc_handler = None
        self._dis_handler = None
        self._bic_handler = None
        self._cac_handler = None

        if not buddy:
            self._key = key
            # connect to the PS's buddy-appeared signal and
            # wait for the buddy to appear
            self._ba_handler = self._pservice.connect('buddy-appeared',
                    self._buddy_appeared_cb)
            # Set color to 'inactive'/'disconnected'
            self._set_color_from_string(_NOT_PRESENT_COLOR)
            self._nick = nick

            self._pservice.get_buddies_async(reply_handler=self._get_buddies_cb)
        else:
            self._update_buddy(buddy)

    def _get_buddies_cb(self, buddy_list):
        buddy = None
        for iter_buddy in buddy_list:
            if iter_buddy.props.key == self._key:
                buddy = iter_buddy
                break

        if buddy:
            if self._ba_handler:
                # Once we have the buddy, we no longer need to
                # monitor buddy-appeared events
                self._pservice.disconnect(self._ba_handler)
                self._ba_handler = None

            self._update_buddy(buddy)

    def is_owner(self):
        return False

    def get_current_activity(self):
        if self._buddy:
            return self._buddy.props.current_activity
        return None

    def is_present(self):
        if self._buddy:
            return True
        return False

    def get_buddy(self):
        return self._buddy

    def _update_buddy(self, buddy):
        if not buddy:
            raise ValueError("Buddy cannot be None.")

        self._buddy = buddy
        self._key = self._buddy.props.key
        self._nick = self._buddy.props.nick
        self._tags = self._buddy.props.tags
        self._set_color_from_string(self._buddy.props.color)
        self.props.present = True

        self._pc_handler = self._buddy.connect('property-changed',
                                               self._buddy_property_changed_cb)

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
        if 'tags' in keys:
            self._tags = self._buddy.props.tags
            self.emit('tags-changed', self.get_tags())

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
        self.props.present = False

