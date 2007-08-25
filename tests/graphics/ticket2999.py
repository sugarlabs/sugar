# Copyright (C) 2007, One Laptop Per Child
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
Spec in ticket #2999.
"""

import gtk

from sugar.graphics.palette import Palette
from sugar.graphics.icon import Icon

import common

test = common.Test()
test.set_border_width(60)

text_view = gtk.TextView()
text_view.props.buffer.props.text = 'Blah blah blah, blah blah blah.'
test.pack_start(text_view)
text_view.show()

if __name__ == "__main__":
    common.main(test)
