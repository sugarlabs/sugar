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

from sugar.graphics.icon import Icon
from sugar.graphics.xocolor import XoColor

import common

test = common.Test()

icon = Icon(icon_name='go-previous')
icon.props.icon_size = gtk.ICON_SIZE_LARGE_TOOLBAR
test.pack_start(icon)
icon.show()

icon = Icon(icon_name='computer-xo', 
            icon_size=gtk.ICON_SIZE_LARGE_TOOLBAR,
            xo_color=XoColor())
test.pack_start(icon)
icon.show()

icon = Icon(icon_name='battery-000',
            icon_size=gtk.ICON_SIZE_LARGE_TOOLBAR,
            badge_name='badge-busy')
test.pack_start(icon)
icon.show()

test.show()

if __name__ == "__main__":
    common.main(test)
