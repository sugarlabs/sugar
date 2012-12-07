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

import os
import unittest

from jarabe.desktop.activitieslist import ActivityListPalette

tests_dir = os.path.dirname(__file__)
data_dir = os.path.join(tests_dir, "data")

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

class TestActivitiesList(unittest.TestCase):
    def test_activity_list_palette(self):
        palette = ActivityListPalette(MockActivityInfo())
