# Copyright (C) 2007, Red Hat, Inc.
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

"""
Test the sugar.graphics.icon.Icon widget.
"""

import gtk

from sugar.graphics.tray import HTray
from sugar.graphics.tray import TrayButton

import common

test = common.Test()

box = gtk.VBox()

tray = HTray()
box.pack_start(tray, False)
tray.show()

theme_icons = gtk.icon_theme_get_default().list_icons()

for i in range(0, 100):
    button = TrayButton(icon_name=theme_icons[i])
    tray.add_item(button)
    button.show()

tray = HTray()
box.pack_start(tray, False)
tray.show()

for i in range(0, 10):
    button = TrayButton(icon_name=theme_icons[i])
    tray.add_item(button)
    button.show()

test.pack_start(box)
box.show()

test.show()

if __name__ == "__main__":
    common.main(test)
