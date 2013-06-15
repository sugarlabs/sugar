# Copyright (C) 2013 Ignacio Rodriguez <ignacio@sugarlabs.org>
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
#

import os

from gi.repository import Gtk
from gi.repository import GConf
from gi.repository import Gdk

from sugar3.graphics.xocolor import XoColor
from sugar3.graphics.icon import Icon
from sugar3.graphics import xoicon

client = GConf.Client.get_default()


def set_icon(icon_name):
    xoicon.set_name(icon_name)
    return 1


def test_run():
    current = client.get_string('/desktop/sugar/user/icon')
    if not current:
        client.set_string('/desktop/sugar/user/icon', 'computer-xo')


def get_icon():
    return xoicon.get_name()


def get_icons():
    icon_theme = Gtk.IconTheme.get_default()
    icon_search_path = icon_theme.get_search_path()

    icons = []
    list_icons = os.listdir(xoicon.get_path())

    color = XoColor(client.get_string('/desktop/sugar/user/color'))

    icon_size = int(Gdk.Screen.width() / 10)
    icon = get_icon()
    my_icon = Icon(icon_name=icon, pixel_size=icon_size, xo_color=color)
    icons.append([my_icon, icon])

    if icon != 'computer-xo':
        my_icon = Icon(icon_name='computer-xo', pixel_size=icon_size,
                       xo_color=color)
        icons.append([my_icon, 'computer-xo'])

    if icon + '.svg' in list_icons:
        list_icons.remove(icon + '.svg')

    for icon in list_icons:
        if not icon.endswith('.svg'):
            continue

        my_icon = Icon(icon_name=icon[:-4], pixel_size=icon_size,
                       xo_color=color)
        icons.append([my_icon, icon[:-4]])

    return icons


LAST_ICON = get_icon()


def undo(store):
    set_icon(LAST_ICON)


test_run()
