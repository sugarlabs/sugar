import re

import gobject
import gtk
import goocanvas
import rsvg

from sugar.util import GObjectSingletonMeta
from sugar.canvas.IconColor import IconColor

_ICON_SIZE = 48

class _IconCache:
	def __init__(self):
		self._icons = {}

	def _create_icon(self, name, color):
		theme = gtk.icon_theme_get_default()
		info = theme.lookup_icon(name, _ICON_SIZE, 0)
		icon_file = open(info.get_filename(), 'r')
		data = icon_file.read()
		icon_file.close()

		if color != None:
			fill = color.get_fill_color()
			stroke = color.get_stroke_color()

			style = '.fill {fill:%s;stroke:%s;}' % (fill, fill)
			data = re.sub('\.fill \{.*\}', style, data)

			style = '.shape {stroke:%s;fill:%s;}' % (stroke, stroke)
			data = re.sub('\.shape \{.*\}', style, data)

			style = '.shape-and-fill {fill:%s; stroke:%s;}' % (fill, stroke)
			data = re.sub('\.shape-and-fill \{.*\}', style, data)

		return data

	def get_icon(self, name, color):
		key = (name, color.get_fill_color())
		if self._icons.has_key(key):
			icon = self._icons[key]
		else:
			icon = self._create_icon(name, color)
			self._icons[key] = icon
		return icon

class IconView(goocanvas.ItemViewSimple, goocanvas.ItemView):
	__gtype_name__ = 'IconView'

	_icon_cache = _IconCache()

	def __init__(self, canvas_view, parent_view, item):
		goocanvas.ItemViewSimple.__init__(self)

		self.parent_view = parent_view
		self.canvas_view = canvas_view
		self.item = item

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

	def do_paint(self, cr, bounds, scale):
		icon_name = self.item.icon_name
		if icon_name == None:
			icon_name = 'stock-missing'

		if self.item.color == None:
			theme = gtk.icon_theme_get_default()
			info = theme.lookup_icon(icon_name, self.item.size, 0)
			handle = rsvg.Handle(file=info.get_filename())
		else:
			icon = IconView._icon_cache.get_icon(icon_name, self.item.color)
			handle = rsvg.Handle(data=icon)			

		cr.save()

		if self.item.transform != None:
			cr.transform(self.item.transform)
		if self.transform != None:
			cr.transform(self.transform)

		cr.translate(self.item.x, self.item.y)
		scale_factor = float(self.item.size) / float(_ICON_SIZE)

		if scale_factor != 0.0:
			cr.scale(scale_factor, scale_factor)		
			handle.render_cairo(cr)

		cr.restore()

		return self.bounds

class IconItem(goocanvas.ItemSimple, goocanvas.Item):
	__gsignals__ = {
		'clicked': (gobject.SIGNAL_RUN_FIRST,
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
		view.connect('button-press-event', self.__button_press_cb)
		return view

	def __button_press_cb(self, view, target, event):
		self.emit('clicked')
