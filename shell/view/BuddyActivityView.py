import hippo
import gobject

import BuddyIcon
from sugar.graphics.canvasicon import CanvasIcon
from sugar.presence import PresenceService
import conf


class BuddyActivityView(hippo.CanvasBox):
	def __init__(self, shell, menu_shell, buddy, **kwargs):
		hippo.CanvasBox.__init__(self, **kwargs)

		self._pservice = PresenceService.get_instance()
		self._activity_registry = conf.get_activity_registry()

		self._buddy = buddy
		self._buddy_icon = BuddyIcon.BuddyIcon(shell, menu_shell, buddy)
		self.append(self._buddy_icon)

		self._activity_icon = CanvasIcon(size=48)
		self._activity_icon_visible = False

		if self._buddy.is_present():
			self._buddy_appeared_cb(buddy)

		self._buddy.connect('current-activity-changed', self._buddy_activity_changed_cb)
		self._buddy.connect('appeared', self._buddy_appeared_cb)
		self._buddy.connect('disappeared', self._buddy_disappeared_cb)
		self._buddy.connect('color-changed', self._buddy_color_changed_cb)

	def _get_new_icon_name(self, activity):
		# FIXME: do something better here; we probably need to use "flagship"
		# services like mDNS where activities default services are marked
		# somehow.
		for serv in activity.get_services():
			act = self._activity_registry.get_activity_from_type(serv.get_type())
			if act:
				return act.get_icon()
		return None

	def _remove_activity_icon(self):
		if self._activity_icon_visible:
			self.remove(self._activity_icon)
			self._activity_icon_visible = False

	def _buddy_activity_changed_cb(self, buddy, activity=None):
		if not activity:
			self._remove_activity_icon()
			return

		# FIXME: use some sort of "unknown activity" icon rather
		# than hiding the icon?
		name = self._get_new_icon_name(activity)
		if name:
			self._activity_icon.props.icon_name = name
			self._activity_icon.props.color = buddy.get_color()
			if not self._activity_icon_visible:
				self.append(self._activity_icon)
				self._activity_icon_visible = True
		else:
			self._remove_activity_icon()

	def _buddy_appeared_cb(self, buddy):
		activity = self._buddy.get_current_activity()
		self._buddy_activity_changed_cb(buddy, activity)

	def _buddy_disappeared_cb(self, buddy):
		self._buddy_activity_changed_cb(buddy, None)

	def _buddy_color_changed_cb(self, buddy, color):
		self._activity_icon.props.color = buddy.get_color()
