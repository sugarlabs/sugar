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

import gtk

from sugar import _sugarext

ICON_ENTRY_PRIMARY = _sugarext.ICON_ENTRY_PRIMARY
ICON_ENTRY_SECONDARY = _sugarext.ICON_ENTRY_SECONDARY

class IconEntry(_sugarext.IconEntry):
    def set_icon_from_name(self, position, name):
        icon_theme = gtk.icon_theme_get_default()
        icon_info = icon_theme.lookup_icon(name,
                                           gtk.ICON_SIZE_SMALL_TOOLBAR,
                                           0)

        pixbuf = gtk.gdk.pixbuf_new_from_file(icon_info.get_filename())

        image = gtk.Image()
        image.set_from_pixbuf(pixbuf)
        image.show()

        self.set_icon(position, image)

    def set_icon(self, position, image):
        if image.get_storage_type() not in [gtk.IMAGE_PIXBUF, gtk.IMAGE_STOCK]:
            raise ValueError('Image must have a storage type of pixbuf or ' +
                             'stock, not %r.' % image.get_storage_type())
        _sugarext.IconEntry.set_icon(self, position, image)

