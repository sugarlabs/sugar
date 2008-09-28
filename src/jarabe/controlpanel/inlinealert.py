# Copyright (C) 2008, OLPC
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

import gtk
import gobject
import pango

from sugar.graphics import style
from sugar.graphics.icon import Icon

class InlineAlert(gtk.HBox):
    """UI interface for Inline alerts

    Inline alerts are different from the other alerts beause they are 
    no dialogs, they only inform about a current event.

    Properties:
        'msg': the message of the alert,
        'icon': the icon that appears at the far left
    See __gproperties__
    """

    __gtype_name__ = 'SugarInlineAlert'

    __gproperties__ = {
        'msg'    : (str, None, None, None,
                    gobject.PARAM_READWRITE),
        'icon'   : (object, None, None,
                    gobject.PARAM_WRITABLE)
        }

    def __init__(self, **kwargs):

        self._msg = None
        self._msg_color = None
        self._icon = Icon(icon_name='emblem-warning',
                          fill_color=style.COLOR_SELECTION_GREY.get_svg(),
                          stroke_color=style.COLOR_WHITE.get_svg())

        self._msg_label = gtk.Label()
        self._msg_label.set_max_width_chars(50)
        self._msg_label.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
        self._msg_label.set_alignment(0, 0.5)
        self._msg_label.modify_fg(gtk.STATE_NORMAL, 
                                  style.COLOR_SELECTION_GREY.get_gdk_color())

        gobject.GObject.__init__(self, **kwargs)

        self.set_spacing(style.DEFAULT_SPACING)
        self.modify_bg(gtk.STATE_NORMAL, 
                       style.COLOR_WHITE.get_gdk_color())
        
        self.pack_start(self._icon, False)
        self.pack_start(self._msg_label, False)
        self._msg_label.show()
        self._icon.show()
        
    def do_set_property(self, pspec, value):        
        if pspec.name == 'msg':
            if self._msg != value:
                self._msg = value
                self._msg_label.set_markup(self._msg)
        elif pspec.name == 'icon':
            if self._icon != value:
                self._icon = value

    def do_get_property(self, pspec):
        if pspec.name == 'msg':
            return self._msg

