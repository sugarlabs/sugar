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

#############################################
# Drawing area tools
#############################################

import gtk
import gtk.gdk

class Drawing_Area_Tools:
    
    height	= 0 
    width	= 0

    margin = 5 # Left and bottom margin

    range_x = []
    range_y = []
    
    def __init__(self, drwarea):
        drwarea_size = drwarea.get_size_request()

        self.width	= drwarea_size[0]
        self.height	= drwarea_size[1]

        # print "width %i" % self.width
        # print "height %i" % self.height
        
        self.range_x = {'from': self.margin+2, 'to': self.width - (self.margin+2)}
        self.range_y = {'from': self.margin+2, 'to': self.height - (self.margin+2)}
                
    def draw_line(self, context, from_x, from_y, to_x, to_y):				
        context.move_to(from_x, from_y)
        context.line_to(to_x, to_y)			
            
    def draw_border_lines(self, context):
        context.set_source_rgb(1, 1, 1)
        self.draw_line(context, self.margin, self.margin, self.margin, self.height - self.margin)
        self.draw_line(context, self.margin, self.height - self.margin - 1, self.width - self.margin, self.height - self.margin - 1)
        context.stroke()
        