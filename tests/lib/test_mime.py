#!/usr/bin/env python

# Copyright (C) 2006, Red Hat, Inc.
# Copyright (C) 2007, One Laptop Per Child
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
import unittest

from sugar import objects

class TestMime(unittest.TestCase):
    def test_from_file_name(self):
        self.assertEqual(objects.mime.get_from_file_name('test.pdf'),
                         'application/pdf')

    def test_choose_most_significant(self):
        # Mozilla's text in dnd
        mime_type = objects.mime.choose_most_significant(
                ['text/plain', 'text/_moz_htmlcontext', 'text/unicode',
                 'text/html', 'text/_moz_htmlinfo'])
        self.assertEqual(mime_type, 'text/html')
        
        # Mozilla's text in c&v
        mime_type = objects.mime.choose_most_significant(
                ['text/_moz_htmlcontext', 'STRING', 'text/html', 'text/_moz_htmlinfo',
                 'text/x-moz-url-priv', 'UTF8_STRING', 'COMPOUND_TEXT'])
        self.assertEqual(mime_type, 'text/html')

        # Mozilla gif in dnd
        mime_type = objects.mime.choose_most_significant(
                ['application/x-moz-file-promise-url',
                 'application/x-moz-file-promise-dest-filename', 'text/_moz_htmlinfo',
                 'text/x-moz-url-desc', 'text/_moz_htmlcontext', 'text/x-moz-url-data',
                 'text/uri-list'])
        self.assertEqual(mime_type, 'text/uri-list')

        # Mozilla url in dnd
        mime_type = objects.mime.choose_most_significant(
                ['text/_moz_htmlcontext', 'text/html', 'text/_moz_htmlinfo',
                 '_NETSCAPE_URL', 'text/x-moz-url', 'text/x-moz-url-desc',
                 'text/x-moz-url-data', 'text/plain', 'text/unicode'])
        self.assertEqual(mime_type, 'text/x-moz-url')

        # Abiword text in dnd
        mime_type = objects.mime.choose_most_significant(
                ['text/rtf', 'text/uri-list'])
        self.assertEqual(mime_type, 'text/uri-list')

        # Abiword text in c&v
        mime_type = objects.mime.choose_most_significant(
                ['UTF8_STRING', 'STRING', 'text/html', 'TEXT', 'text/rtf',
                 'COMPOUND_TEXT', 'application/rtf', 'text/plain',
                 'application/xhtml+xml'])
        self.assertEqual(mime_type, 'application/rtf')

if __name__ == "__main__":
    unittest.main()

