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

import sys
import os
import unittest
import subprocess

from jarabe import config
from jarabe.webservice.account import Account

ACCOUNT_NAME = 'mock'

tests_dir = os.path.dirname(__file__)
extension_dir = os.path.join(tests_dir, 'extensions')
web_extension_dir = os.path.join(extension_dir, 'web')


def _create_main_toolbox():
    from gi.repository import Gtk
    from jarabe.journal.journaltoolbox import MainToolbox

    toolbox = MainToolbox()
    toolbox.show()

    Gtk.main()


def _create_detail_toolbox():
    from gi.repository import Gtk
    from jarabe.journal.journaltoolbox import DetailToolbox

    toolbox = DetailToolbox()
    toolbox.show()

    Gtk.main()


class TestDetailToolBox(unittest.TestCase):
    def setUp(self):
        os.environ["MOCK_ACCOUNT_STATE"] = str(Account.STATE_VALID)
        self.save_ext_path = config.ext_path
        config.ext_path = extension_dir
        sys.path.append(config.ext_path)

    def _check_detail_toolbox(self):
        from sugar3.test import uitree

        root = uitree.get_root()

        # 'Clipboard', ACCOUNT_NAME
        for name in ['Duplicate', 'Erase']:
            node = root.find_child(name=name, role_name='label')
            self.assertIsNotNone(node)

    def test_detail_toolbox(self):
        process = subprocess.Popen(['python', __file__,
                                    '_create_detail_toolbox'])
        try:
            self._check_detail_toolbox()
        finally:
            process.terminate()

    def tearDown(self):
        sys.path.remove(config.ext_path)
        config.ext_path = self.save_ext_path

if __name__ == '__main__':
    globals()[sys.argv[1]]()
