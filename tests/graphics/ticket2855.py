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
Test the style of toggle and radio buttons inside a palette. The buttons
contains only an icon and should be rendered similarly to the toolbar
controls. Ticket #2855.
"""

import gtk

from sugar.graphics.palette import Palette
from sugar.graphics.icon import Icon

import common

test = common.TestPalette()

palette = Palette('Test radio and toggle')
test.set_palette(palette)

box = gtk.HBox()

toggle = gtk.ToggleButton()

icon = Icon(icon_name='go-previous', icon_size=gtk.ICON_SIZE_LARGE_TOOLBAR)
toggle.set_image(icon)

box.pack_start(toggle, False)
toggle.show()

radio = gtk.RadioButton()

icon = Icon(icon_name='go-next', icon_size=gtk.ICON_SIZE_LARGE_TOOLBAR)
radio.set_image(icon)

radio.set_mode(False)
box.pack_start(radio, False)
radio.show()

palette.set_content(box)
box.show()

if __name__ == "__main__":
    common.main(test)
