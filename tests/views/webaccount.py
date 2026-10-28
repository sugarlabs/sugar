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

import os
import sys

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

from jarabe import config
from jarabe.webservice.account import Account
from jarabe.webservice import accountsmanager

ACCOUNT_NAME = 'mock'

tests_dir = os.getcwd()
extension_dir = os.path.join(tests_dir, 'extensions')

os.environ["MOCK_ACCOUNT_STATE"] = str(Account.STATE_VALID)
config.ext_path = extension_dir
sys.path.append(config.ext_path)

window = Gtk.Window()
box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
box.set_visible(True)
window.set_child(box)

services = accountsmanager.get_webaccount_services()
for service in services:
    if service.get_icon_name() == ACCOUNT_NAME:
        service.config_service_cb(None, None, box)

window.present()

import GLib
GLib.MainLoop().run()
