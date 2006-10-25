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

import random

from sugar.graphics.colors import colors

def _parse_string(color_string):
	if color_string == 'white':
		return ['#ffffff', '#414141']

	splitted = color_string.split(',')
	if len(splitted) == 2:
		return [splitted[0], splitted[1]]
	else:
		return None

def is_valid(color_string):
	return (_parse_string(color_string) != None)

class IconColor:
	def __init__(self, color_string=None):
		if color_string == None or not is_valid(color_string):
			n = int(random.random() * (len(colors) - 1))
			[self._stroke, self._fill] = colors[n]
		else:
			[self._stroke, self._fill] = _parse_string(color_string)

	def get_stroke_color(self):
		return self._stroke

	def get_fill_color(self):
		return self._fill

	def to_string(self):
		return '%s,%s' % (self._stroke, self._fill)

