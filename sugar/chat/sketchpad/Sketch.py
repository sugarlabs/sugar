from SVGdraw import path

class Sketch:
	def __init__(self):
		self._points = []
	
	def add_point(self, x, y):
		self._points.append([x, y])
		
	def draw(self, ctx):
		start = True
		for [x, y] in self._points:
			if start:
				ctx.move_to(x, y)
				start = False
			else:
				ctx.line_to(x, y)
		ctx.stroke()
	
	def draw_to_svg(self):
		i = 0
		for [x, y] in self._points:
			coords = str(x) + ' ' + str(y) + ' '
			if i == 0:
				path_data = 'M ' + coords
			elif i == 1:
				path_data += 'L ' + coords
			else:
				path_data += coords
			i += 1
		return path(path_data, fill = 'none', stroke = '#000000')
