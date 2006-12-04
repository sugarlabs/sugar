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

import os
import random
import base64
import time
import logging
import dbus

from sugar import env
from sugar import profile
from sugar.p2p import Stream
from sugar.presence import PresenceService
from sugar import util
from model.Invites import Invites

PRESENCE_SERVICE_TYPE = "_presence_olpc._tcp"

class ShellOwner(object):
    """Class representing the owner of this machine/instance.  This class
    runs in the shell and serves up the buddy icon and other stuff.  It's the
    server portion of the Owner, paired with the client portion in Buddy.py."""
    def __init__(self):
        self._nick = profile.get_nick_name()
        user_dir = env.get_profile_path()

        self._icon = None
        self._icon_hash = ""
        for fname in os.listdir(user_dir):
            if not fname.startswith("buddy-icon."):
                continue
            fd = open(os.path.join(user_dir, fname), "r")
            self._icon = fd.read()
            if self._icon:
                # Get the icon's hash
                import md5, binascii
                digest = md5.new(self._icon).digest()
                self._icon_hash = util.printable_hash(digest)
            fd.close()
            break

        self._pservice = PresenceService.get_instance()

        self._invites = Invites()

        self._last_activity_update = time.time()
        self._pending_activity_update_timer = None
        self._pending_activity_update = None

    def get_invites(self):
        return self._invites

    def get_name(self):
        return self._nick

    def announce(self):
        # Create and announce our presence
        color = profile.get_color()
        props = {'color': color.to_string(), 'icon-hash': self._icon_hash}
        self._service = self._pservice.register_service(self._nick,
                PRESENCE_SERVICE_TYPE, properties=props)
        logging.debug("Owner '%s' using port %d" % (self._nick, self._service.get_port()))
        self._icon_stream = Stream.Stream.new_from_service(self._service)
        self._icon_stream.register_reader_handler(self._handle_buddy_icon_request, "get_buddy_icon")
        self._icon_stream.register_reader_handler(self._handle_invite, "invite")

    def _handle_buddy_icon_request(self):
        """XMLRPC method, return the owner's icon encoded with base64."""
        if self._icon:
            return base64.b64encode(self._icon)
        return ""

    def _handle_invite(self, issuer, bundle_id, activity_id):
        """XMLRPC method, called when the owner is invited to an activity."""
        self._invites.add_invite(issuer, bundle_id, activity_id)
        return ''

    def __update_advertised_current_activity_cb(self):
        self._last_activity_update = time.time()
        self._pending_activity_update_timer = None
        if self._pending_activity_update:
            logging.debug("*** Updating current activity to %s" % self._pending_activity_update)
            self._service.set_published_value('curact', dbus.String(self._pending_activity_update))
        return False

    def set_current_activity(self, activity_id):
        """Update our presence service with the latest activity, but no
        more frequently than every 30 seconds"""
        self._pending_activity_update = activity_id
        # If there's no pending update, we must not have updated it in the
        # last 30 seconds (except for the initial update, hence we also check
        # for the last update)
        if not self._pending_activity_update_timer or time.time() - self._last_activity_update > 30:
            self.__update_advertised_current_activity_cb()
            return

        # If we have a pending update already, we have nothing left to do
        if self._pending_activity_update_timer:
            return

        # Otherwise, we start a timer to update the activity at the next
        # interval, which should be 30 seconds from the last update, or if that
        # is in the past already, then now
        next = 30 - max(30, time.time() - self._last_activity_update)
        self._pending_activity_update_timer = gobject.timeout_add(next * 1000,
                self.__update_advertised_current_activity_cb)
