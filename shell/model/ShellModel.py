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

from sugar.presence import PresenceService
from sugar.activity.bundleregistry import BundleRegistry
from model.Friends import Friends
from model.MeshModel import MeshModel
from model.Owner import ShellOwner
from sugar import env

class ShellModel:
    def __init__(self):
        self._current_activity = None

        self._bundle_registry = BundleRegistry()

        PresenceService.start()
        self._pservice = PresenceService.get_instance()

        self._owner = ShellOwner()
        self._owner.announce()

        self._friends = Friends()
        self._mesh = MeshModel(self._bundle_registry)

        path = os.path.expanduser('~/Activities')
        self._bundle_registry.add_search_path(path)

        for path in env.get_data_dirs():
            bundles_path = os.path.join(path, 'activities')
            self._bundle_registry.add_search_path(bundles_path)

    def get_bundle_registry(self):
        return self._bundle_registry

    def get_mesh(self):
        return self._mesh

    def get_friends(self):
        return self._friends

    def get_invites(self):
        return self._owner.get_invites()

    def get_owner(self):
        return self._owner

    def set_current_activity(self, activity_id):
        self._current_activity = activity_id
        self._owner.set_current_activity(activity_id)

    def get_current_activity(self):
        return self._current_activity
