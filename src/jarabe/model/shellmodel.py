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

import wnck
import gobject

from sugar.presence import presenceservice
from jarabe.model.Friends import Friends
from jarabe.model.MeshModel import MeshModel
from jarabe.model.homemodel import HomeModel
from jarabe.model.Owner import ShellOwner
from jarabe.model.devices.devicesmodel import DevicesModel

class ShellModel(gobject.GObject):
    ZOOM_MESH = 0
    ZOOM_FRIENDS = 1
    ZOOM_HOME = 2
    ZOOM_ACTIVITY = 3

    __gproperties__ = {
        'zoom-level' : (int, None, None,
                        0, 3, ZOOM_HOME,
                        gobject.PARAM_READABLE)
    }

    def __init__(self):
        gobject.GObject.__init__(self)

        self._current_activity = None
        self._zoom_level = self.ZOOM_HOME
        self._showing_desktop = True

        self._pservice = presenceservice.get_instance()

        self._owner = ShellOwner()

        self._friends = Friends()
        self._mesh = MeshModel()
        self._home = HomeModel()
        self._devices = DevicesModel()

        self._screen = wnck.screen_get_default()
        self._screen.connect('showing-desktop-changed',
                             self._showing_desktop_changed_cb)

    def set_zoom_level(self, level):
        self._zoom_level = level
        self.notify('zoom-level')

    def get_zoom_level(self):
        if self._screen.get_showing_desktop():
            return self._zoom_level
        else:
            return self.ZOOM_ACTIVITY

    def do_get_property(self, pspec):
        if pspec.name == 'zoom-level':
            return self.get_zoom_level()                

    def get_mesh(self):
        return self._mesh

    def get_friends(self):
        return self._friends

    def get_invites(self):
        return self._owner.get_invites()

    def get_home(self):
        return self._home

    def get_owner(self):
        return self._owner

    def get_devices(self):
        return self._devices

    def _showing_desktop_changed_cb(self, screen):
        showing_desktop = self._screen.get_showing_desktop()
        if self._showing_desktop != showing_desktop:
            self._showing_desktop = showing_desktop
            self.notify('zoom-level')

_instance = None

def get_instance():
    global _instance
    if not _instance:
        _instance = ShellModel()
    return _instance

