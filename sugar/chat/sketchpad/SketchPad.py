import gtk

from Sketch import Sketch

from SVGdraw import drawing
from SVGdraw import svg

class SketchPad(gtk.DrawingArea):
	def __init__(self):
		gtk.DrawingArea.__init__(self)

		self._active_sketch = None
		self._rgb = (0.0, 0.0, 0.0)
		self._sketches = []

		self.add_events(gtk.gdk.BUTTON_PRESS_MASK |
						gtk.gdk.BUTTON1_MOTION_MASK)
		self.connect("button-press-event", self.__button_press_cb)
		self.connect("button-release-event", self.__button_release_cb)
		self.connect("motion-notify-event", self.__motion_notify_cb)
		self.connect('expose_event', self.expose)
	
	def clear(self):
		self._sketches = []
		self.window.invalidate_rect(None, False)

	def expose(self, widget, event):
		"""Draw the background of the sketchpad."""
		rect = self.get_allocation()
		ctx = widget.window.cairo_create()
		
		ctx.set_source_rgb(0.6, 1, 0.4)
		ctx.rectangle(0, 0, rect.width, rect.height)
		ctx.fill_preserve()
		
		ctx.set_source_rgb(0, 0.3, 0.2)
		ctx.stroke()
		
		for sketch in self._sketches:
			sketch.draw(ctx)
		
		return False

	def set_color(self, color):
		"""Sets the current drawing color of the sketchpad.
		color agument should be 3-item tuple of rgb values between 0 and 1."""
		self._rgb = color

	def add_sketch(self, sketch):
		self._sketches.append(sketch)
	
	def add_point(self, event):
		if self._active_sketch:
			self._active_sketch.add_point(event.x, event.y)	
		self.window.invalidate_rect(None, False)
	
	def __button_press_cb(self, widget, event):
		self._active_sketch = Sketch(self._rgb)
		self.add_sketch(self._active_sketch)
		self.add_point(event)
	
	def __button_release_cb(self, widget, event):
		self.add_point(event)
		self._active_sketch = None
	
	def __motion_notify_cb(self, widget, event):
		self.add_point(event)
	
	def to_svg(self):
		"""Return a string containing an SVG representation of this sketch."""
		d = drawing()
		s = svg()
		for sketch in self._sketches:
			s.addElement(sketch.draw_to_svg())
		d.setSVG(s)
		return d.toXml()

def test_quit(w, skpad):
	print skpad.to_svg()
	gtk.main_quit()

if __name__ == "__main__":
	window = gtk.Window()
	window.set_default_size(400, 300)
	window.connect("destroy", lambda w: gtk.main_quit())
        
	sketchpad = SketchPad()
	window.add(sketchpad)
	sketchpad.show()
	
	window.show()
	
	window.connect("destroy", test_quit, sketchpad)

	gtk.main()
