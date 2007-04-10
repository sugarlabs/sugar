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

import gobject
import os
import random
import base64
import time
import logging
import dbus

from sugar import env
from sugar import profile
from sugar.presence import presenceservice
from sugar import util
from model.Invites import Invites

class ShellOwner(gobject.GObject):
    __gtype_name__ = "ShellOwner"

    __gsignals__ = {
        'nick-changed'                : (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                                        ([gobject.TYPE_STRING])),
        'color-changed'               : (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                                        ([gobject.TYPE_PYOBJECT])),
        'icon-changed'                : (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                                        ([gobject.TYPE_PYOBJECT]))
    }

    """Class representing the owner of this machine/instance.  This class
    runs in the shell and serves up the buddy icon and other stuff.  It's the
    server portion of the Owner, paired with the client portion in Buddy.py."""
    def __init__(self):
        gobject.GObject.__init__(self)

        self._nick = profile.get_nick_name()

        self._icon = None
        self._icon_hash = ""
        icon = os.path.join(env.get_profile_path(), "buddy-icon.jpg")
        if not os.path.exists(icon):
            raise RuntimeError("missing buddy icon")

        fd = open(icon, "r")
        self._icon = fd.read()
        fd.close()
        if not self._icon:
            raise RuntimeError("invalid buddy icon")

        # Get the icon's hash
        import md5
        digest = md5.new(self._icon).digest()
        self._icon_hash = util.printable_hash(digest)

        self._pservice = presenceservice.get_instance()

        self._invites = Invites()

    def get_invites(self):
        return self._invites

    def get_nick(self):
        return self._nick

    def _handle_invite(self, issuer, bundle_id, activity_id):
        """XMLRPC method, called when the owner is invited to an activity."""
        self._invites.add_invite(issuer, bundle_id, activity_id)
        return ''
