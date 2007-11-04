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
"""

import gtk
import gobject

from sugar import _sugarext

import common

def _preview_timeout_cb():
    preview = _sugarext.Preview()
    preview.take_screenshot(button.window)
    preview.get_pixbuf().save('/home/marco/test.png','png')
    preview.clear()

test = common.Test()

button = gtk.Button('Hello')
test.pack_start(button)
button.show()

gobject.timeout_add(2000, _preview_timeout_cb)

if __name__ == "__main__":
    common.main(test)
