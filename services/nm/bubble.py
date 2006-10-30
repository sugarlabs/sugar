# Copyright (C) 2006, Red Hat, Inc.
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

import math

import gobject
import gtk
import hippo

class Bubble(hippo.CanvasBox, hippo.CanvasItem):
	__gtype_name__ = 'NetworkBubble'

	__gproperties__ = {
		'color'    : (object, None, None,
					  gobject.PARAM_READWRITE),
		'percent'  : (object, None, None,
					  gobject.PARAM_READWRITE),
	}

	def __init__(self, **kwargs):
		self._color = None
		self._percent = 0
		self._radius = 8

		hippo.CanvasBox.__init__(self, **kwargs)

	def do_set_property(self, pspec, value):
		if pspec.name == 'color':
			self._color = value
			self.emit_paint_needed(0, 0, -1, -1)
		elif pspec.name == 'percent':
			self._percent = value
			self.emit_paint_needed(0, 0, -1, -1)

	def do_get_property(self, pspec):
		if pspec.name == 'color':
			return self._color
		elif pspec.name == 'percent':
			return self._percent

	def _string_to_rgb(self, color_string):
		col = gtk.gdk.color_parse(color_string)
		return (col.red / 65535.0, col.green / 65535.0, col.blue / 65535.0)

	def do_paint_below_children(self, cr, damaged_box):
		[width, height] = self.get_allocation()

		line_width = 3.0
		x = line_width
		y = line_width
		width -= line_width * 2
		height -= line_width * 2

		cr.move_to(x + self._radius, y);
		cr.arc(x + width - self._radius, y + self._radius,
			   self._radius, math.pi * 1.5, math.pi * 2);
		cr.arc(x + width - self._radius, x + height - self._radius,
			   self._radius, 0, math.pi * 0.5);
		cr.arc(x + self._radius, y + height - self._radius,
			   self._radius, math.pi * 0.5, math.pi);
		cr.arc(x + self._radius, y + self._radius, self._radius,
			   math.pi, math.pi * 1.5);

		color = self._string_to_rgb(self._color.get_fill_color())
		cr.set_source_rgb(*color)
		cr.fill_preserve();

		color = self._string_to_rgb(self._color.get_stroke_color())
		cr.set_source_rgb(*color)
		cr.set_line_width(line_width)
		cr.stroke();
