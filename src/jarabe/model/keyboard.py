# Copyright (C) 2006, Red Hat, Inc.
# Copyright (C) 2009, One Laptop Per Child Association Inc
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

import logging

import gi
from gi.repository import Gio
from gi.repository import GdkX11


def setup():
    settings = Gio.Settings.new('org.sugarlabs.peripherals.keyboard')
    have_config = False

    logging.debug('setup_keyboard_cb: Could not get default display.')
    return
