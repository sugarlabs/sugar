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
Test the sugar.graphics.icon.* cache.
"""

import gtk

from sugar.graphics.icon import Icon
from sugar.graphics.xocolor import XoColor
from sugar import logger

logger.start('iconcache')

import common

test = common.Test()

data = [
    ['battery-000', '#FF8F00,#FF2B34'],
    ['battery-010', '#D1A3FF,#00A0FF'],
    ['battery-020', '#FF8F00,#FF2B34'],
    ['battery-030', '#00A0FF,#D1A3FF'],
    ['battery-040', '#AC32FF,#FF2B34'],
    ['battery-050', '#D1A3FF,#00A0FF'],
    ['battery-060', '#AC32FF,#FF2B34'],
    ['battery-070', '#00A0FF,#D1A3FF'],
    ['battery-080', '#FF8F00,#FF2B34'],
    ['battery-090', '#D1A3FF,#00A0FF'],
    ['battery-100', '#AC32FF,#FF2B34']]

def _button_activated_cb(button):
    import random

    global data
    random.shuffle(data)

    for i in range(0, len(test.get_children()) - 1):
        test.get_children()[i].props.icon_name = data[i][0]
        test.get_children()[i].props.xo_color = XoColor(data[i][1])

for d in data:
    icon = Icon(icon_name=d[0],
                icon_size=gtk.ICON_SIZE_LARGE_TOOLBAR,
                xo_color=XoColor(d[1]))
    test.pack_start(icon)
    icon.show()

button = gtk.Button("mec mac")
test.pack_start(button)
button.connect('activate', _button_activated_cb)
button.show()

test.show()

if __name__ == "__main__":
    common.main(test)
