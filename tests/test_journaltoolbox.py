# Copyright (C) 2012, Daniel Narvaez
# Copyright (C) 2013, Walter Bender
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from sugar3.test import unittest
from sugar3.test import uitree

ACCOUNT_NAME = 'mock'


class TestDetailToolBox(unittest.UITestCase):

    def test_detail_toolbox(self):
        with self.run_view("journal_detailstoolbox"):
            root = uitree.get_root()

            for name in ['Clipboard', ACCOUNT_NAME]:
                node = root.find_child(name=name, role_name='menu item')
                self.assertIsNotNone(node)
