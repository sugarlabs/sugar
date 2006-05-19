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
