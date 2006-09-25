import goocanvas

import BuddyIcon
from sugar.canvas.IconItem import IconItem
from sugar.presence import PresenceService
import conf
import gobject


class BuddyActivityView(goocanvas.Group):
	__gproperties__ = {
		'x'        : (float, None, None, -10e6, 10e6, 0,
					  gobject.PARAM_READWRITE),
		'y'        : (float, None, None, -10e6, 10e6, 0,
					  gobject.PARAM_READWRITE),
		'size'     : (float, None, None,
					  0, 1024, 24,
					  gobject.PARAM_READABLE)
	}

	def __init__(self, shell, menu_shell, buddy, **kwargs):
		goocanvas.Group.__init__(self, **kwargs)

		self._pservice = PresenceService.get_instance()
		self._activity_registry = conf.get_activity_registry()

		self._buddy = buddy
		self._x = 0
		self._y = 0

		self._buddy_icon = BuddyIcon.BuddyIcon(shell, menu_shell, buddy)
		self.add_child(self._buddy_icon)
		self._activity_icon = IconItem(size=48)
		self._activity_icon_visible = False
		curact = self._buddy.get_current_activity()
		if curact:
			self.__buddy_activity_changed_cb(self._buddy, activity=curact)

		self._buddy.connect('current-activity-changed', self.__buddy_activity_changed_cb)
		self._buddy.connect('appeared', self.__buddy_presence_change_cb)
		self._buddy.connect('disappeared', self.__buddy_presence_change_cb)
		self._buddy.connect('color-changed', self.__buddy_presence_change_cb)

	def do_set_property(self, pspec, value):
		if pspec.name == 'x':
			self._x = value
			self._buddy_icon.props.x = value + 20
			self._activity_icon.props.x = value
		elif pspec.name == 'y':
			self._y = value
			self._buddy_icon.props.y = value
			self._activity_icon.props.y = value + 50

	def do_get_property(self, pspec):
		if pspec.name == 'x':
			return self._x
		elif pspec.name == 'y':
			return self._y
		elif pspec.name == 'size':
			return self._recompute_size()

	def _recompute_size(self):
		bi_size = self._buddy_icon.props.size
		bi_x = self._buddy_icon.props.x
		bi_y = self._buddy_icon.props.y
		acti_size = self._activity_icon.props.size
		acti_x = self._activity_icon.props.x
		acti_y = self._activity_icon.props.y

		# Union the two rectangles
		dest_x = min(bi_x, acti_x)
		dest_y = min(bi_y, acti_y)
		dest_width = max(bi_x + bi_size, acti_x + acti_size) - dest_x
		dest_height = max(bi_y + bi_size, acti_y + acti_size) - dest_y

		# IconLayout can't deal with rectangular sizes yet
		dest_size = max(dest_width, dest_height)
		return dest_size

	def _get_new_icon_name(self, activity):
		# FIXME: do something better here; we probably need to use "flagship"
		# services like mDNS where activities default services are marked
		# somehow.
		for serv in activity.get_services():
			act = self._activity_registry.get_activity_from_type(serv.get_type())
			if act:
				return act.get_icon()
		return None

	def __buddy_activity_changed_cb(self, buddy, activity=None):
		if not activity:
			self.remove_child(self._activity_icon)
			self._activity_icon_visible = False
			return

		name = self._get_new_icon_name(activity)
		if name:
			self._activity_icon.props.icon_name = name
			self._activity_icon.props.color = self._buddy_icon.props.color
		if not self._activity_icon_visible:
			self.add_child(self._activity_icon)
			self._activity_icon_visible = True

	def __buddy_presence_change_cb(self, buddy, color=None):		
		self._activity_icon.props.color = buddy.get_color()
