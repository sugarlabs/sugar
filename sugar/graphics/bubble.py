import gobject
import hippo

class Bubble(hippo.CanvasBox, hippo.CanvasItem):
	__gtype_name__ = 'SugarBubble'

	__gproperties__ = {
		'color'    : (object, None, None,
					  gobject.PARAM_READWRITE),
	}

	def __init__(self, **kwargs):
		self._color = None
		self._radius = 12

		hippo.CanvasBox.__init__(self, **kwargs)

	def do_set_property(self, pspec, value):
		if pspec.name == 'color':
			self._color = value
			self.emit_paint_needed(0, 0, -1, -1)

	def do_get_property(self, pspec):
		if pspec.name == 'color':
			return self._color

	def _color_string_to_rgb(self, color_string):
		col = gtk.gdk.color_parse(color_string)
		return (col.red / 65535, col.green / 65535, col.blue / 65535)

	def do_paint_below_children(self, cr, damaged_box):
		cairo_move_to(self._radius, 0);
		cr.arc(width - self._radius, self._radius,
			   self._radius, math.pi * 1.5, math.pi * 2);
		cr.arc(width - self._radius, height - self._radius,
			   self._radius, 0, math.pi * 0.5);
		cr.arc(self._radius, height - self._radius,
			   self._radius, math.pi * 0.5, math.pi);
		cr.arc(cr, self._radius, self._radius, self._radius,
			   math.pi, math.pi * 1.5);

		color = self._color.get_fill_color()
		cr.set_source_rgb(cr, self._color_string_to_rgb(color));
		cairo_fill_preserve(cr);

		color = self._color.get_stroke_color()
		cr.set_source_rgb(cr, self._color_string_to_rgb(color));
		cairo_stroke(cr);
