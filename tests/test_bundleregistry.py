# Copyright (C) 2013, One Laptop per Child
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

from gi.repository import GLib
import shutil
import tempfile
import unittest
import os

from jarabe.model import bundleregistry
from sugar3.bundle.helpers import bundle_from_archive

GLib.threads_init()

tests_dir = os.getcwd()
data_dir = os.path.join(tests_dir, "data")
base_dir = os.path.dirname(tests_dir)

os.environ["SUGAR_MIME_DEFAULTS"] = \
    os.path.join(base_dir, "data", "mime.defaults")


class TestBundleRegistry(unittest.TestCase):
    def setUp(self):
        activities_path = tempfile.mkdtemp()
        library_path = tempfile.mkdtemp()
        os.environ['SUGAR_ACTIVITIES_PATH'] = activities_path
        os.environ['SUGAR_LIBRARY_PATH'] = library_path

    def tearDown(self):
        activities_path = os.environ.pop('SUGAR_ACTIVITIES_PATH', None)
        if activities_path:
            shutil.rmtree(activities_path)

        library_path = os.environ.pop('SUGAR_LIBRARY_PATH', None)
        if library_path:
            shutil.rmtree(library_path)

    def test_install_content(self):
        registry = bundleregistry.get_registry()
        bundle = bundle_from_archive(os.path.join(data_dir, 'sample-1.xol'))
        registry.install(bundle)
        installed_bundle = registry.get_bundle("org.sugarlabs.samplecontent")
        self.assertIsNotNone(installed_bundle)

    def test_install_activity(self):
        registry = bundleregistry.get_registry()
        bundle = bundle_from_archive(os.path.join(data_dir, 'activity-1.xo'))
        registry.install(bundle)
        installed_bundle = registry.get_bundle("org.sugarlabs.MyActivity")
        self.assertIsNotNone(installed_bundle)
