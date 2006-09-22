import re

import gobject
import gtk
import goocanvas
import rsvg
import cairo

from sugar.util import GObjectSingletonMeta
from sugar.canvas.IconColor import IconColor

class _IconCache:
	def __init__(self):
		self._icons = {}
		self._theme = gtk.icon_theme_get_default()

	def _read_icon(self, filename, color):
		icon_file = open(filename, 'r')

		if color == None:
			return rsvg.Handle(file=filename)
		else:
			data = icon_file.read()
			icon_file.close()

			fill = color.get_fill_color()
			stroke = color.get_stroke_color()

			style = '.fill {fill:%s;stroke:%s;}' % (fill, fill)
			data = re.sub('\.fill \{.*\}', style, data)

			style = '.shape {stroke:%s;fill:%s;}' % (stroke, stroke)
			data = re.sub('\.shape \{.*\}', style, data)

			style = '.shape-and-fill {fill:%s; stroke:%s;}' % (fill, stroke)
			data = re.sub('\.shape-and-fill \{.*\}', style, data)

			return rsvg.Handle(data=data)

	def get_handle(self, name, color, size):
		info = self._theme.lookup_icon(name, int(size), 0)

		if color:
			key = (info.get_filename(), color.to_string())
		else:
			key = info.get_filename()

		if self._icons.has_key(key):
			icon = self._icons[key]
		else:
			icon = self._read_icon(info.get_filename(), color)
			self._icons[key] = icon
		return icon

class IconView(goocanvas.ItemViewSimple, goocanvas.ItemView):
	__gtype_name__ = 'IconView'

	_cache = _IconCache()

	def __init__(self, canvas_view, parent_view, item):
		goocanvas.ItemViewSimple.__init__(self)

		self.parent_view = parent_view
		self.canvas_view = canvas_view
		self.item = item

		self._buffer = None
		self._buffer_size = 0.0

		item.connect('changed', goocanvas.item_view_simple_item_changed, self)

	def do_get_item_view_at(self, x, y, cr, is_pointer_event, parent_is_visible):
		result = self

		cr.save()

		if self.item.transform != None:
			cr.transform(self.item.transform)
		if self.transform != None:
			cr.transform(self.transform)

		[user_x, user_y] = cr.device_to_user(x, y)
		if user_x < self.item.x or \
		   user_x > self.item.x + self.item.size or \
		   user_y < self.item.y or \
		   user_y > self.item.y + self.item.size:
			result = None

		cr.restore()

		return result

	def do_update(self, entire_tree, cr):
		if entire_tree or self.flags & goocanvas.ITEM_VIEW_NEED_UPDATE:
			self.flags &= ~goocanvas.ITEM_VIEW_NEED_UPDATE

			cr.save()

			if self.item.transform != None:
				cr.transform(self.item.transform)
			if self.transform != None:
				cr.transform(self.transform)

			self.get_canvas_view().request_redraw(self.bounds)

			bounds = goocanvas.Bounds()
			bounds.x1 = self.item.x
			bounds.y1 = self.item.y
			bounds.x2 = self.item.x + self.item.size
			bounds.y2 = self.item.y + self.item.size
			self.item.user_bounds_to_device(cr, bounds)
			self.bounds = bounds

			self.get_canvas_view().request_redraw(self.bounds)

			cr.restore()

		return self.bounds

	def _get_buffer(self, cr, handle, size):
		if self._buffer and self._buffer_size != size:
			del self._buffer
			self._buffer = None

		if self._buffer == None:
			target = cr.get_target()
			surface = target.create_similar(cairo.CONTENT_COLOR_ALPHA,
						 			        int(size) + 1, int(size) + 1)

			dimensions = handle.get_dimension_data()
			scale = size / dimensions[0]

			ctx = cairo.Context(surface)
			ctx.scale(scale, scale)
			handle.render_cairo(ctx)
			del ctx

			self._buffer = surface
			self._buffer_scale = scale

		return self._buffer

	def do_paint(self, cr, bounds, scale):
		icon_name = self.item.icon_name
		if icon_name == None:
			icon_name = 'stock-missing'

		handle = IconView._cache.get_handle(
				icon_name, self.item.color, self.item.size)
		buf = self._get_buffer(cr, handle, self.item.size)

		cr.save()

		if self.item.transform != None:
			cr.transform(self.item.transform)
		if self.transform != None:
			cr.transform(self.transform)

		cr.translate(self.item.x, self.item.y)
		cr.set_source_surface(buf, 0.0, 0.0)
		cr.paint()

		cr.restore()

		return self.bounds

class IconItem(goocanvas.ItemSimple, goocanvas.Item):
	__gsignals__ = {
		'clicked': (gobject.SIGNAL_RUN_FIRST,
					gobject.TYPE_NONE, ([])),
		'popup':   (gobject.SIGNAL_RUN_FIRST,
					gobject.TYPE_NONE, ([int, int, int, int])),
		'popdown': (gobject.SIGNAL_RUN_FIRST,
					gobject.TYPE_NONE, ([])),
	}

	__gproperties__ = {
		'x'        : (float, None, None, -10e6, 10e6, 0,
					  gobject.PARAM_READWRITE),
		'y'        : (float, None, None, -10e6, 10e6, 0,
					  gobject.PARAM_READWRITE),
		'icon-name': (str, None, None, None,
					  gobject.PARAM_READWRITE),
		'color'    : (object, None, None,
					  gobject.PARAM_READWRITE),
		'size'     : (float, None, None,
					  0, 1024, 24,
					  gobject.PARAM_READWRITE)
	}

	def __init__(self, **kwargs):
		self.x = 0.0
		self.y = 0.0
		self.size = 24
		self.color = None
		self.icon_name = None

		goocanvas.ItemSimple.__init__(self, **kwargs)

	def do_set_property(self, pspec, value):
		recompute_bounds = False

		if pspec.name == 'icon-name':
			self.icon_name = value
		elif pspec.name == 'color':
			self.color = value
		elif pspec.name == 'size':
			self.size = value
			recompute_bounds = True
		elif pspec.name == 'x':
			self.x = value
			recompute_bounds = True
		elif pspec.name == 'y':
			self.y = value
			recompute_bounds = True

		self.emit('changed', recompute_bounds)

	def do_get_property(self, pspec):
		if pspec.name == 'x':
			return self.x
		elif pspec.name == 'y':
			return self.y
		elif pspec.name == 'size':
			return self.size
		elif pspec.name == 'icon-name':
			return self.icon_name
		elif pspec.name == 'color':
			return self.color

	def do_create_view(self, canvas, parent_view):
		view = IconView(canvas, parent_view, self)
		view.connect('button-press-event', self._button_press_cb)
		return view

	def _button_press_cb(self, view, target, event):
		self.emit('clicked')
