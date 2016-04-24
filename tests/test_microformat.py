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

import unittest
import os

from sugar3.bundle.bundleversion import NormalizedVersion

from jarabe.model.update.microformat import _UpdateHTMLParser
from jarabe.model.update.microformat import MetadataLookup

tests_dir = os.getcwd()
data_dir = os.path.join(tests_dir, "data")


class TestMicroformat(unittest.TestCase):
    def test_html_parser(self):
        parser = _UpdateHTMLParser("http://www.sugarlabs.org")
        fd = open(os.path.join(data_dir, "microformat.html"), "r")
        parser.feed(fd.read())
        parser.close()

        results = parser.results
        self.assertIn('org.sugarlabs.AbacusActivity', results.keys())
        self.assertIn('org.laptop.WebActivity', results.keys())

        # test that we picked the newest version
        version, url = results['org.sugarlabs.AbacusActivity']
        self.assertEqual(NormalizedVersion("43"), version)
        self.assertEqual("http://download.sugarlabs.org/abacus-43.xo", url)

        # test resolve relative url
        version, url = results['org.laptop.WebActivity']
        self.assertEqual("http://www.sugarlabs.org/browse-149.xo", url)

    def test_zip_name_lookup(self):
        fd = open(os.path.join(data_dir, "activity-1.xo"))
        lookup = MetadataLookup(None)
        name = lookup._name_from_fd(fd)
        self.assertEqual("My Activity", name)
