import random

from sugar.canvas import Colors

def _parse_string(color_string):
	if color_string == 'white':
		return ['#4f4f4f', 'white']

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
			n = int(random.random() * (len(Colors.colors) - 1))
			[self._fill, self._stroke] = Colors.colors[n]
		else:
			[self._fill, self._stroke] = _parse_string(color_string)

	def get_stroke_color(self):
		return self._stroke

	def get_fill_color(self):
		return self._fill

	def to_string(self):
		return '%s,%s' % (self._fill, self._stroke)

