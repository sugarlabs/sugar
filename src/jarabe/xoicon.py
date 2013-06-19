# Copyright (C) 2013 Ignacio Rodriguez
# Copyright (C) 2013 Walter Bender
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import os
import logging

from gi.repository import Gtk
from gi.repository import GConf

from jarabe.journal.model import get_documents_path


def get_path():
    path = get_documents_path()
    if path is not None:
        icon_theme = Gtk.IconTheme.get_default()
        icon_search_path = icon_theme.get_search_path()
        if path not in icon_search_path:
            icon_theme.append_search_path(path)

    return path


def get_name():
    client = GConf.Client.get_default()
    icon_name = client.get_string('/desktop/sugar/user/icon')
    if icon_name is not None:
        get_path()
        return icon_name
    else:
        return "computer-xo"


def set_name(icon_name):
    if icon_name is not None:
        client = GConf.Client.get_default()
        client.set_string('/desktop/sugar/user/icon', icon_name)
