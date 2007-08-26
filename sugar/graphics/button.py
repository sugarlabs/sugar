# Copyright (C) 2007 Red Hat, Inc.
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

import hippo
import gtk

from sugar.graphics.icon import Icon

class CanvasButton(hippo.CanvasButton):
    def __init__(self, label, icon_name=None):
        hippo.CanvasButton.__init__(self, text=label)

        if icon_name:
            icon = Icon(icon_name=icon_name, icon_size=gtk.ICON_SIZE_BUTTON)
            self.props.widget.set_image(icon)
            icon.show()

        
