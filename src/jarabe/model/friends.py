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

import os
import logging
from ConfigParser import ConfigParser

import gobject
import dbus

from sugar import env
from sugar.graphics.xocolor import XoColor

from jarabe.model.buddy import BuddyModel
from jarabe.model import neighborhood


_model = None


class FriendBuddyModel(BuddyModel):
    __gtype_name__ = 'SugarFriendBuddyModel'

    _NOT_PRESENT_COLOR = '#D5D5D5,#FFFFFF'

    def __init__(self, nick, key):
        self._online_buddy = None

        BuddyModel.__init__(self, nick=nick, key=key)

        neighborhood_model = neighborhood.get_model()
        neighborhood_model.connect('buddy-added', self.__buddy_added_cb)
        neighborhood_model.connect('buddy-removed', self.__buddy_removed_cb)

        buddy = neighborhood_model.get_buddy_by_key(key)
        if buddy is not None:
            self._set_online_buddy(buddy)

    def __buddy_added_cb(self, neighborhood, buddy):
        if buddy.key != self.key:
            return
        self._set_online_buddy(buddy)

    def _set_online_buddy(self, buddy):
        self._online_buddy = buddy
        self._online_buddy.connect('notify::color', self.__notify_color_cb)
        self.notify('color')
        self.notify('present')

    def __buddy_removed_cb(self, neighborhood, buddy):
        if buddy.key != self.key:
            return
        self._online_buddy = None
        self.notify('color')
        self.notify('present')

    def __notify_color_cb(self, buddy, pspec):
        self.notify('color')

    def is_present(self):
        return self._online_buddy is not None

    present = gobject.property(type=bool, default=False, getter=is_present)

    def get_color(self):
        if self._online_buddy is not None:
            return self._online_buddy.color
        else:
            return XoColor(FriendBuddyModel._NOT_PRESENT_COLOR)

    color = gobject.property(type=object, getter=get_color)

    def get_handle(self):
        if self._online_buddy is not None:
            return self._online_buddy.handle
        else:
            return None

    handle = gobject.property(type=object, getter=get_handle)


class Friends(gobject.GObject):
    __gsignals__ = {
        'friend-added': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                         ([object])),
        'friend-removed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                           ([str])),
    }

    def __init__(self):
        gobject.GObject.__init__(self)

        self._friends = {}
        self._path = os.path.join(env.get_profile_path(), 'friends')

        self.load()

    def has_buddy(self, buddy):
        return buddy.get_key() in self._friends

    def add_friend(self, buddy_info):
        self._friends[buddy_info.get_key()] = buddy_info
        self.emit('friend-added', buddy_info)

    def make_friend(self, buddy):
        if not self.has_buddy(buddy):
            buddy = FriendBuddyModel(key=buddy.key, nick=buddy.nick)
            self.add_friend(buddy)
            self.save()

    def remove(self, buddy_info):
        del self._friends[buddy_info.get_key()]
        self.save()
        self.emit('friend-removed', buddy_info.get_key())

    def __iter__(self):
        return self._friends.values().__iter__()

    def load(self):
        cp = ConfigParser()

        try:
            success = cp.read([self._path])
            if success:
                for key in cp.sections():
                    # HACK: don't screw up on old friends files
                    if len(key) < 20:
                        continue
                    buddy = FriendBuddyModel(key=key, nick=cp.get(key, 'nick'))
                    self.add_friend(buddy)
        except Exception:
            logging.exception('Error parsing friends file')

    def save(self):
        cp = ConfigParser()

        for friend in self:
            section = friend.get_key()
            cp.add_section(section)
            cp.set(section, 'nick', friend.get_nick())

        fileobject = open(self._path, 'w')
        cp.write(fileobject)
        fileobject.close()

        self._sync_friends()

    def _sync_friends(self):
        # XXX: temporary hack
        # remove this when the shell service has a D-Bus API for buddies

        def friends_synced():
            pass

        def friends_synced_error(e):
            logging.error('Error asking presence service to sync friends: %s',
                e)

        keys = []
        for friend in self:
            keys.append(friend.get_key())

        bus = dbus.SessionBus()
        ps = bus.get_object('org.laptop.Sugar.Presence',
            '/org/laptop/Sugar/Presence')
        psi = dbus.Interface(ps, 'org.laptop.Sugar.Presence')
        psi.SyncFriends(keys,
                reply_handler=friends_synced,
                error_handler=friends_synced_error)


def get_model():
    global _model
    if _model is None:
        _model = Friends()
    return _model
