# Copyright (C) 2006-2007 Red Hat, Inc.
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
import os
import gconf
import simplejson

from sugar import env
from sugar import util

class Owner(gobject.GObject):
    """Class representing the owner of this machine/instance. This class
    runs in the shell and serves up the buddy icon and other stuff. It's the
    server portion of the Owner, paired with the client portion in Buddy.py.
    """
    __gtype_name__ = "ShellOwner"

    __gsignals__ = {
        'nick-changed'  : (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                           ([gobject.TYPE_STRING])),
        'color-changed' : (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                           ([gobject.TYPE_PYOBJECT])),
        'icon-changed'  : (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                           ([gobject.TYPE_PYOBJECT]))
    }

    def __init__(self):
        gobject.GObject.__init__(self)

        client = gconf.client_get_default()
        self._nick = client.get_string("/desktop/sugar/user/nick")

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
        import hashlib
        digest = hashlib.md5(self._icon).digest()
        self._icon_hash = util.printable_hash(digest)

    def get_nick(self):
        return self._nick

_model = None

def get_model():
    global _model
    if _model is None:
        _model = Owner()
    return _model
