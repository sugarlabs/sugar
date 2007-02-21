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
import gobject
import hippo

class PopupContext(gobject.GObject):
    __gtype_name__ = 'SugarPopupContext'

    __gsignals__ = {
        'activated':   (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
        'deactivated': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([]))
    }
    
    def __init__(self):
        self._active_control = None
        gobject.GObject.__init__(self)

    def popped_up(self, control):
        if self._active_control:
            self._active_control.popdown()
        self._active_control = control
        self.emit('activated')

    def popped_down(self, control):
        if self._active_control == control:
            self._active_control = None
        self.emit('deactivated')

    def is_active(self):
        return self._active_control != None

    def get_position(self, control, popup):
        return [None, None]
