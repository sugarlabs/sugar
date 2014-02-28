# Copyright (C) 2014, Gonzalo Odiard
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

import unittest
import sys

from jarabe import config

# we need import from the extensions path
sys.path.append(config.ext_path)

from cpsection.backup.backupmanager import BackupManager
from cpsection.backup.backends.backend_tools import Backend


class TestBackup(unittest.TestCase):

    def setUp(self):
        self.manager = BackupManager()
        self._backends = self.manager.get_backends()

    def test_get_backend(self):
        self.assertTrue(len(self._backends) > 0)

    def test_backend_backup_restore(self):
        for backend in self._backends:
            # verify the backend have the methods needed
            self.assertIsInstance(backend.get_name(), str)

            self.assertIsInstance(backend.get_backup(), Backend)

            self.assertIsInstance(backend.get_restore(), Backend)

    def test_need_stop_activities(self):
        self.assertFalse(self.manager.need_stop_activities())
