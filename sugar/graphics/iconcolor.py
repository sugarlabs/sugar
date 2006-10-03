import random

from sugar.graphics.colors import colors

def _parse_string(color_string):
	if color_string == 'white':
		return ['#ffffff', '#4f4f4f']

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

