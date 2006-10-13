import math

import gobject
import gtk
import hippo

class Bubble(hippo.CanvasBox, hippo.CanvasItem):
	__gtype_name__ = 'SugarBubble'

	__gproperties__ = {
		'color'    : (object, None, None,
					  gobject.PARAM_READWRITE),
	}

	def __init__(self, **kwargs):
		self._color = None
		self._radius = 8

		hippo.CanvasBox.__init__(self, **kwargs)

	def do_set_property(self, pspec, value):
		if pspec.name == 'color':
			self._color = value
			self.emit_paint_needed(0, 0, -1, -1)

	def do_get_property(self, pspec):
		if pspec.name == 'color':
			return self._color

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
