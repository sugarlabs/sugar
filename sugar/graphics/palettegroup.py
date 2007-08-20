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

import gobject

_groups = {}

def get_group(group_id):
    if _groups.has_key(group_id):
        group = _groups[group_id]
    else:
        group = Group()
        _groups[group_id] = group

    return group

class Group(gobject.GObject):
    __gsignals__ = {
        'popup' : (gobject.SIGNAL_RUN_FIRST,
                     gobject.TYPE_NONE, ([])),
        'popdown' : (gobject.SIGNAL_RUN_FIRST,
                     gobject.TYPE_NONE, ([]))
    }
    def __init__(self):
        gobject.GObject.__init__(self)
        self._up = False
        self._palettes = []

    def is_up(self):
        return self._up

    def add(self, palette):
        self._palettes.append(palette)

        sid = palette.connect('popup', self._palette_popup_cb)
        palette.popup_sid = sid

        sid = palette.connect('popdown', self._palette_popdown_cb)
        palette.podown_sid = sid

    def remove(self, palette):
        self.disconnect(palette.popup_sid)
        self.disconnect(palette.popdown_sid)

        self._palettes.remove(palette)

    def popdown(self):
        for palette in self._palettes:
            if palette.is_up(): 
                palette.popdown(immediate=True)

    def _palette_popup_cb(self, palette):
        if not self._up:
            self.emit('popup')
            self._up = True

    def _palette_popdown_cb(self, palette):
        down = True
        for palette in self._palettes:
            if palette.is_up():
                down = False

        if down:
            self._up = False
            self.emit('popdown')
