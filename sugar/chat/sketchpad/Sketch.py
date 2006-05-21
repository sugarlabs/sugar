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
