import goocanvas

import BuddyIcon
from sugar.canvas.IconItem import IconItem
from sugar.presence import PresenceService
import conf
import gobject


class BuddyActivityView(goocanvas.Group):
	def __init__(self, shell, menu_shell, buddy, **kwargs):
		goocanvas.Group.__init__(self, **kwargs)

		self._pservice = PresenceService.get_instance()
		self._activity_registry = conf.get_activity_registry()

		self._buddy = buddy
		self._buddy_icon = BuddyIcon.BuddyIcon(shell, menu_shell, buddy)
		self.add_child(self._buddy_icon)

		buddy_size = self._buddy_icon.props.size
		offset_y = buddy_size
		offset_x = (buddy_size - 48) / 2
		self._activity_icon = IconItem(x=offset_x, y=offset_y, size=48)
		self._activity_icon_visible = False

		if self._buddy.is_present():
			self.__buddy_appeared_cb(buddy)

		self._buddy.connect('current-activity-changed', self.__buddy_activity_changed_cb)
		self._buddy.connect('appeared', self.__buddy_appeared_cb)
		self._buddy.connect('disappeared', self.__buddy_disappeared_cb)
		self._buddy.connect('color-changed', self.__buddy_color_changed_cb)

	def get_size_request(self):
		bi_size = self._buddy_icon.props.size
		acti_size = self._activity_icon.props.size

		width = bi_size
		height = bi_size + acti_size

		return [width, height]

	def _get_new_icon_name(self, activity):
		# FIXME: do something better here; we probably need to use "flagship"
		# services like mDNS where activities default services are marked
		# somehow.
		for serv in activity.get_services():
			act = self._activity_registry.get_activity_from_type(serv.get_type())
			if act:
				return act.get_icon()
		return None

	def __remove_activity_icon(self):
		if self._activity_icon_visible:
			self.remove_child(self._activity_icon)
			self._activity_icon_visible = False

	def __buddy_activity_changed_cb(self, buddy, activity=None):
		if not activity:
			self.__remove_activity_icon()
			return

		# FIXME: use some sort of "unknown activity" icon rather
		# than hiding the icon?
		name = self._get_new_icon_name(activity)
		if name:
			self._activity_icon.props.icon_name = name
			self._activity_icon.props.color = buddy.get_color()
			if not self._activity_icon_visible:
				self.add_child(self._activity_icon)
				self._activity_icon_visible = True
		else:
			self.__remove_activity_icon()

	def __buddy_appeared_cb(self, buddy):
		activity = self._buddy.get_current_activity()
		self.__buddy_activity_changed_cb(buddy, activity)

	def __buddy_disappeared_cb(self, buddy):
		self.__buddy_activity_changed_cb(buddy, None)

	def __buddy_color_changed_cb(self, buddy, color):
		self._activity_icon.props.color = buddy.get_color()
