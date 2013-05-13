# Copyright (C) 2012, Daniel Narvaez
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

import sys
import os
import unittest
import subprocess

tests_dir = os.path.dirname(__file__)
base_dir = os.path.dirname(tests_dir)
data_dir = os.path.join(tests_dir, "data")

os.environ["SUGAR_ACTIVITIES_DEFAULTS"] = \
    os.path.join(base_dir, "data", "activities.defaults")
os.environ["SUGAR_MIME_DEFAULTS"] = \
    os.path.join(base_dir, "data", "mime.defaults")


class MockActivityInfo:
    def get_bundle_id(self):
        return "mock"

    def get_activity_version(self):
        return 1

    def get_is_favorite(self):
        return False

    def get_icon(self):
        return os.path.join(data_dir, "activity.svg")

    def get_name(self):
        return "mock"

    def get_path(self):
        return "mock"

    def is_user_activity(self):
        return True


def _create_activities_palette():
    from gi.repository import Gtk
    from jarabe.desktop.activitieslist import ActivityListPalette

    palette = ActivityListPalette(MockActivityInfo())
    palette.popup()

    Gtk.main()


class TestActivitiesList(unittest.TestCase):
    def _check_activities_palette(self):
        from sugar3.test import uitree

        root = uitree.get_root()

        for name in ["Make favorite", "Erase", "Start new"]:
            node = root.find_child(name=name, role_name="label")
            self.assertIsNotNone(node)

    def test_activity_list_palette(self):
        process = subprocess.Popen(["python", __file__,
                                    "_create_activities_palette"])
        try:
            self._check_activities_palette()
        finally:
            process.terminate()

if __name__ == '__main__':
    globals()[sys.argv[1]]()
