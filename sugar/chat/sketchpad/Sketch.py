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

from SVGdraw import path

class Sketch:
	def __init__(self, rgb):
		self._points = []
		self._rgb = (float(rgb[0]), float(rgb[1]), float(rgb[2]))
	
	def add_point(self, x, y):
		self._points.append((x, y))
		
	def draw(self, ctx):
		start = True
		for (x, y) in self._points:
			if start:
				ctx.move_to(x, y)
				start = False
			else:
				ctx.line_to(x, y)
		ctx.set_source_rgb(self._rgb[0], self._rgb[1], self._rgb[2])
		ctx.stroke()
	
	def draw_to_svg(self):
		i = 0
		for (x, y) in self._points:
			coords = str(x) + ' ' + str(y) + ' '
			if i == 0:
				path_data = 'M ' + coords
			elif i == 1:
				path_data += 'L ' + coords
			else:
				path_data += coords
			i += 1
		color = "#%02X%02X%02X" % (255 * self._rgb[0], 255 * self._rgb[1], 255 * self._rgb[2])
		return path(path_data, fill = 'none', stroke = color)
