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

import gobject
import gconf

from sugar.presence import presenceservice
from sugar.graphics.xocolor import XoColor

from jarabe.util.telepathy import connection_watcher

_NOT_PRESENT_COLOR = "#d5d5d5,#FFFFFF"

CONNECTION_INTERFACE_BUDDY_INFO = 'org.laptop.Telepathy.BuddyInfo'

class BaseBuddyModel(gobject.GObject):
    __gtype_name__ = 'SugarBaseBuddyModel'

    def __init__(self, **kwargs):
        self._key = None
        self._nick = None
        self._color = None
        self._tags = None
        self._present = False

        gobject.GObject.__init__(self, **kwargs)

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

    def set_key(self, key):
        self._key = key

    key = gobject.property(type=object, getter=get_key, setter=set_key)

    def get_color(self):
        return self._color

    def set_color(self, color):
        self._color = color

    color = gobject.property(type=object, getter=get_color, setter=set_color)

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

        client = gconf.client_get_default()
        self.props.nick = client.get_string("/desktop/sugar/user/nick")
        self.props.color = XoColor(client.get_string("/desktop/sugar/user/color"))

        self.connect('notify::nick', self.__property_changed_cb)
        self.connect('notify::color', self.__property_changed_cb)

        logging.info('KILL_PS should set the properties before the connection'
                     'is connected, if possible')
        conn_watcher = connection_watcher.get_instance()
        conn_watcher.connect('connection-added', self.__connection_added_cb)

        self._sync_properties()

    def __property_changed_cb(self, pspec):
        self._sync_properties()

    def _sync_properties(self):
        conn_watcher = connection_watcher.get_instance()
        for connection in conn_watcher.get_connections():
            self._sync_properties_on_connection(connection)

    def _sync_properties_on_connection(self, connection):
        if CONNECTION_INTERFACE_BUDDY_INFO in connection:
            properties = {}
            if self.props.key is not None:
                properties['key'] = self.props.key
            if self.props.color is not None:
                properties['color'] = self.props.color.to_string()

            logging.debug('calling SetProperties with %r', properties)
            connection[CONNECTION_INTERFACE_BUDDY_INFO].SetProperties(
                properties,
                reply_handler=self.__set_properties_cb,
                error_handler=self.__error_handler_cb)

    def __set_properties_cb(self):
        logging.debug('__set_properties_cb')

    def __error_handler_cb(self, error):
        raise RuntimeError(error)

    def __connection_added_cb(self, conn_watcher, connection):
        self._sync_properties_on_connection(connection)

    def is_owner(self):
        return True

    def get_buddy(self):
        return None

class BuddyModel(BaseBuddyModel):
    __gtype_name__ = 'SugarBuddyModel'
    def __init__(self, **kwargs):

        self._account = None
        self._contact_id = None

        BaseBuddyModel.__init__(self, **kwargs)

    def is_owner(self):
        return False

    def get_current_activity(self):
        return None

    def get_buddy(self):
        raise NotImplementedError

    def get_account(self):
        return self._account

    def set_account(self, account):
        self._account = account

    account = gobject.property(type=object, getter=get_account,
                               setter=set_account)

    def get_contact_id(self):
        return self._contact_id

    def set_contact_id(self, contact_id):
        self._contact_id = contact_id

    contact_id = gobject.property(type=object, getter=get_contact_id,
                                  setter=set_contact_id)

"""        
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

    def _set_color_from_string(self, color_string):
        self._color = XoColor(color_string)

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
"""

class FriendBuddyModel(BuddyModel):
    __gtype_name__ = 'SugarFriendBuddyModel'
    def __init__(self, nick, key):
        BuddyModel.__init__(self, nick=nick, key=key)

