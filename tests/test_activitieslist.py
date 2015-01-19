# Copyright (C) 2013, Daniel Narvaez
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

from sugar3.test import unittest
from sugar3.test import uitree


class TestActivitiesList(unittest.UITestCase):

    def test_activity_list_palette(self):
        with self.run_view("activitieslist"):
            root = uitree.get_root()

            for name in ["Make favorite", "Erase", "Start new"]:
                node = root.find_child(name=name, role_name="label")
                self.assertIsNotNone(node)
