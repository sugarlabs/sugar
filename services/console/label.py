#!/usr/bin/env python

# Copyright (C) 2007, Eduardo Silva (edsiper@gmail.com).
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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import gtk
import pango

class Label(gtk.Label):
    TITLE = 0
    DESCRIPTION = 1
    
    def __init__(self, text, font_type):
        gtk.Label.__init__(self)
        
        self.set_text(text)
        self.set_alignment(0.0, 0.5)

        s = {
            self.TITLE: self._set_title_font,
            self.DESCRIPTION: self._set_description_font
        }[font_type]()
        
    def _set_title_font(self):
        font = pango.FontDescription('Sans 12')
        font.set_weight(pango.WEIGHT_NORMAL)
        self.modify_font(font)

    def _set_description_font(self):
        font = pango.FontDescription('Sans 8')
        font.set_weight(pango.WEIGHT_NORMAL)
        self.modify_font(font)

class Style:
    
    def set_title_font(self, object):
        font = pango.FontDescription('Sans 20')
        font.set_weight(pango.WEIGHT_NORMAL)
        object.modify_font(font)

