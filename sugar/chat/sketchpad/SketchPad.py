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

import gtk

from Sketch import Sketch

from SVGdraw import drawing
from SVGdraw import svg

class SketchPad(gtk.DrawingArea):
	def __init__(self, bgcolor=(0.6, 1, 0.4)):
		gtk.DrawingArea.__init__(self)

		self._active_sketch = None
		self._rgb = (0.0, 0.0, 0.0)
		self._bgcolor = bgcolor
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
		
		ctx.set_source_rgb(self._bgcolor[0], self._bgcolor[1], self._bgcolor[2])
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
