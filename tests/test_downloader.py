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

import os
import unittest
import threading
import SimpleHTTPServer
import SocketServer

from gi.repository import Gtk
from gi.repository import GLib

from sugar3 import env
from jarabe.util.downloader import Downloader

profile_data_dir = os.path.join(env.get_profile_path(), 'data')
if not os.path.isdir(profile_data_dir):
        os.makedirs(profile_data_dir)

tests_dir = os.getcwd()
data_dir = os.path.join(tests_dir, "data")

GLib.threads_init()


class TestDownloader(unittest.TestCase):
    def setUp(self):
        handler = SimpleHTTPServer.SimpleHTTPRequestHandler
        self._server = SocketServer.TCPServer(("", 0), handler)
        self._port = self._server.server_address[1]
        self._server_thread = threading.Thread(target=self._run_http_server)
        self._server_thread.daemon = True
        self._server_thread.start()

    def tearDown(self):
        self._server.shutdown()
        self._server_thread.join()

    def _run_http_server(self):
        self._server.serve_forever()

    def download_complete_cb(self, downloader, result):
        self._complete = True
        self._result = result

    def test_download_to_temp(self):
        downloader = Downloader("http://0.0.0.0:%d/data/test.txt" % self._port)
        self._complete = False
        downloader.connect('complete', self.download_complete_cb)
        downloader.download_to_temp()

        while not self._complete:
            Gtk.main_iteration()

        self.assertIsNone(self._result)
        path = downloader.get_local_file_path()
        text = open(path, "r").read()
        self.assertEqual("hello\n", text)

    def test_download(self):
        downloader = Downloader("http://0.0.0.0:%d/data/test.txt" % self._port)
        self._complete = False
        downloader.connect('complete', self.download_complete_cb)
        downloader.download()

        while not self._complete:
            Gtk.main_iteration()

        self.assertEqual("hello\n", self._result.get_data())

    def test_get_size(self):
        downloader = Downloader("http://0.0.0.0:%d/data/test.txt" % self._port)
        self._complete = False
        downloader.connect('complete', self.download_complete_cb)
        downloader.get_size()

        while not self._complete:
            Gtk.main_iteration()

        self.assertEqual(6, self._result)
