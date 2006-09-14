import re

import gobject
import gtk
import goocanvas
import rsvg
import cairo

from sugar.util import GObjectSingletonMeta
from sugar.canvas.IconColor import IconColor

_ICON_SIZE = 48

class _IconCache:
	def __init__(self):
		self._icons = {}

	def _read_icon(self, name, color):
		theme = gtk.icon_theme_get_default()
		info = theme.lookup_icon(name, _ICON_SIZE, 0)
		icon_file = open(info.get_filename(), 'r')

		if color == None:
			return rsvg.Handle(file=info.get_filename())
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

	def get_handle(self, name, color):
		if color:
			key = (name, color.to_string())
		else:
			key = name

		if self._icons.has_key(key):
			icon = self._icons[key]
		else:
			icon = self._read_icon(name, color)
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
		self._buffer_scale = 0.0

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

	def _get_buffer(self, cr, handle, scale):
		if self._buffer and self._buffer_scale != scale:
			del self._buffer
			self._buffer = None

		if self._buffer == None:
			size = int(_ICON_SIZE * scale)
			surface = cr.get_target().create_similar(
							cairo.CONTENT_COLOR_ALPHA, size, size)

			ctx = cairo.Context(surface)
			ctx.scale(scale, scale)
			handle.render_cairo(ctx)
			del ctx

			self._buffer = surface
			self._buffer_scale = scale

		return self._buffer

	def do_paint(self, cr, bounds, scale):
		scale_factor = float(self.item.size) / float(_ICON_SIZE)
		if scale_factor == 0.0:
			return

		icon_name = self.item.icon_name
		if icon_name == None:
			icon_name = 'stock-missing'

		handle = IconView._cache.get_handle(icon_name, self.item.color)
		buf = self._get_buffer(cr, handle, scale_factor)

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
		'size'     : (int, None, None,
					  0, 1024, 24,
					  gobject.PARAM_READWRITE)
	}

	def __init__(self, **kwargs):
		self.x = 0.0
		self.y = 0.0
		self.size = 24
		self.color = None
		self.icon_name = None
		self._popdown_timeout = 0

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
		view.connect('enter-notify-event', self._enter_notify_event_cb, canvas)
		view.connect('leave-notify-event', self._leave_notify_event_cb)
		return view

	def _button_press_cb(self, view, target, event):
		self.emit('clicked')

	def _start_popdown_timeout(self):
		self._stop_popdown_timeout()
		self._popdown_timeout = gobject.timeout_add(1000, self._popdown)

	def _stop_popdown_timeout(self):
		if self._popdown_timeout > 0:
			gobject.source_remove(self._popdown_timeout)
			self._popdown_timeout = 0

	def _enter_notify_event_cb(self, view, target, event, canvas):
		self._stop_popdown_timeout()

		[x1, y1] = canvas.convert_to_pixels(view.get_bounds().x1,
								 		    view.get_bounds().y1)
		[x2, y2] = canvas.convert_to_pixels(view.get_bounds().x2,
								 		    view.get_bounds().y2)

		[window_x, window_y] = canvas.window.get_origin()

		x1 += window_x
		y1 += window_y
		x2 += window_x
		y2 += window_y

		self.emit('popup', int(x1), int(y1), int(x2), int(y2))

	def _popdown(self):
		self._popdown_timeout = 0
		self.emit('popdown')
		return False

	def _leave_notify_event_cb(self, view, target, event):
		self._start_popdown_timeout()
