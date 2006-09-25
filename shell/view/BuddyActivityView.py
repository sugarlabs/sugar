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

		curact = self._buddy.get_current_activity()
		if curact:
			self.__buddy_activity_changed_cb(self._buddy, activity=curact)

		self._buddy.connect('current-activity-changed', self.__buddy_activity_changed_cb)
		self._buddy.connect('appeared', self.__buddy_presence_change_cb)
		self._buddy.connect('disappeared', self.__buddy_presence_change_cb)
		self._buddy.connect('color-changed', self.__buddy_presence_change_cb)

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
