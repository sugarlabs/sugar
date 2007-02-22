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

import gobject

from sugar.presence import PresenceService
from sugar.activity.bundleregistry import BundleRegistry
from model.Friends import Friends
from model.MeshModel import MeshModel
from model.homemodel import HomeModel
from model.Owner import ShellOwner
from model.devices.devicesmodel import DevicesModel
from sugar import env

class ShellModel(gobject.GObject):
    STATE_STARTUP = 0
    STATE_RUNNING = 1
    STATE_SHUTDOWN = 2

    __gproperties__ = {
        'state'     : (int, None, None,
                      0, 2, STATE_RUNNING,
                      gobject.PARAM_READWRITE)
    }

    def __init__(self):
        gobject.GObject.__init__(self)

        self._current_activity = None
        self._state = self.STATE_RUNNING

        PresenceService.start()
        self._pservice = PresenceService.get_instance()

        self._owner = ShellOwner()
        self._owner.announce()

        self._friends = Friends()
        self._mesh = MeshModel()
        self._home = HomeModel()
        self._devices = DevicesModel()

    def do_set_property(self, pspec, value):
        if pspec.name == 'state':
            self._state = value

    def do_get_property(self, pspec):
        if pspec.name == 'state':
            return self._state

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
