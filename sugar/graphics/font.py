# Copyright (C) 2006-2007, Red Hat, Inc.
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

import pango

from sugar.graphics import units

_system_fonts = {
    'default'       : 'Bitstream Vera Sans %d' % units.points_to_device(7),
    'default-bold'  : 'Bitstream Vera Sans bold %d' % units.points_to_device(7)
}

class Font(object):
    def __init__(self, desc):
        self._desc = desc

    def get_desc(self):
        return self._desc

    def get_pango_desc(self):
        return pango.FontDescription(self._desc)

class SystemFont(Font):
    def __init__(self, font_id):
        Font.__init__(self, _system_fonts[font_id])

DEFAULT = SystemFont('default')
DEFAULT_BOLD = SystemFont('default-bold')
