# Copyright (C) 2006-2007 Red Hat, Inc.
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

class Icon(gtk.Image):
    def __init__(self, name, size=gtk.ICON_SIZE_LARGE_TOOLBAR):
        gtk.Image.__init__(self)

        icon_theme = gtk.icon_theme_get_for_screen(self.get_screen())
        icon_set = gtk.IconSet()

        normal_name = name
        if icon_theme.has_icon(normal_name):
            source = gtk.IconSource()
            source.set_icon_name(normal_name)
            icon_set.add_source(source)

        inactive_name = name + '-inactive'
        if icon_theme.has_icon(inactive_name):
            source = gtk.IconSource()
            source.set_icon_name(inactive_name)
            source.set_state(gtk.STATE_INSENSITIVE)
            icon_set.add_source(source)
            
        self.set_from_icon_set(icon_set, size)

