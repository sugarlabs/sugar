# Copyright (C) 2012, Daniel Narvaez
# Copyright (C) 2013, Walter Bender
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
import sys

from sugar3.test import unittest
from sugar3.test import uitree

from jarabe import config
from jarabe.webservice.account import Account

ACCOUNT_NAME = 'mock'

tests_dir = os.getcwd()
extension_dir = os.path.join(tests_dir, 'extensions')


class TestDetailToolBox(unittest.UITestCase):
    def setUp(self):
        unittest.UITestCase.setUp(self)

        os.environ["MOCK_ACCOUNT_STATE"] = str(Account.STATE_VALID)
        self.save_ext_path = config.ext_path
        config.ext_path = extension_dir
        sys.path.append(config.ext_path)

    def test_detail_toolbox(self):
        with self.run_view("journal_detailstoolbox"):
            root = uitree.get_root()

            for name in [ACCOUNT_NAME]:
                node = root.find_child(name=name, role_name='menu item')
                self.assertIsNotNone(node)

    def tearDown(self):
        unittest.UITestCase.tearDown(self)

        sys.path.remove(config.ext_path)
        config.ext_path = self.save_ext_path
