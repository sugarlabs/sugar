# Copyright (C) 2007, Eduardo Silva (edsiper@gmail.com)
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

import gtk
from sugar.graphics.icon import Icon

class MenuItem(gtk.ImageMenuItem):
    def __init__(self, text_label, icon_name=None):
        gtk.ImageMenuItem.__init__(self, text_label)
        if icon_name:
            icon = Icon(icon_name, gtk.ICON_SIZE_SMALL_TOOLBAR)
            self.set_image(icon)
            icon.show()

