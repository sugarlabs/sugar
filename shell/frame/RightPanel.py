import goocanvas

from frame.PanelWindow import PanelWindow
from sugar.canvas.IconItem import IconItem
from sugar.canvas.IconColor import IconColor
from sugar.presence import PresenceService

class FriendsGroup(goocanvas.Group):
	N_BUDDIES = 10

	def __init__(self, shell, friends, width):
		goocanvas.Group.__init__(self)
		self._shell = shell
		self._friends = friends
		self._width = width
		self._activity_ps = None
		self._joined_hid = -1
		self._left_hid = -1

		self._pservice = PresenceService.get_instance()
		self._pservice.connect('activity-appeared',
							   self.__activity_appeared_cb)

		self._buddies = []
		i = 0
		while i < FriendsGroup.N_BUDDIES:
			self.add_child(self._create_placeholder(i))
			self._buddies.append(None)
			i += 1

		shell.connect('activity-changed', self.__activity_changed_cb)

	def add(self, buddy):
		i = 0
		while i < FriendsGroup.N_BUDDIES:
			if self._buddies[i] == None:
				self._add_buddy(buddy, i)
				break
			i += 1

	def remove(self, buddy):
		i = 0
		while i < FriendsGroup.N_BUDDIES:
			if self._buddies[i] == buddy.get_name():
				self._remove_buddy(buddy, i)
				break
			i += 1

	def clear(self):
		i = 0
		while i < FriendsGroup.N_BUDDIES:
			if self._buddies[i] != None:
				self._remove_buddy(i)
			i += 1

	def _get_y(self, i):
		return i * (self._width + 6)

	def _add_buddy(self, buddy, i):
		self.remove_child(i)
		icon = IconItem(icon_name='stock-buddy',
				        color=IconColor(buddy.get_color()),
						size=self._width, y=self._get_y(i))
		icon.connect('clicked', self.__buddy_clicked_cb, buddy)
		self.add_child(icon, i)
		self._buddies[i] = buddy.get_name()

	def _create_placeholder(self, i):
		icon = IconItem(icon_name='stock-buddy', color=IconColor('white'),
						y=self._get_y(i), size=self._width)
		return icon

	def _remove_buddy(self, i):
		self.remove_child(i)
		self.add_child(self._create_placeholder(i), i)
		self._buddies[i] = None

	def __activity_appeared_cb(self, pservice, activity_ps):
		activity = self._shell.get_current_activity()
		if activity_ps.get_id() == activity.get_id():
			self._set_activity_ps(activity_ps)

	def _set_activity_ps(self, activity_ps):
		if self._activity_ps == activity_ps:
			return

		if self._joined_hid > 0:
			self._activity_ps.disconnect(self._joined_hid)
			self._joined_hid = -1
		if self._left_hid > 0:
			self._activity_ps.disconnect(self._left_hid)
			self._left_hid = -1

		self._activity_ps = activity_ps

		self.clear()

		if activity_ps != None:
			for buddy in activity_ps.get_joined_buddies():
				self.add(buddy)

			self._joined_hid = activity_ps.connect(
							'buddy-joined', self.__buddy_joined_cb)
			self._left_hid = activity_ps.connect(
							'buddy-left', self.__buddy_left_cb)

	def __activity_changed_cb(self, group, activity):
		activity_ps = self._pservice.get_activity(activity.get_id())
		self._set_activity_ps(activity_ps)				

	def __buddy_joined_cb(self, activity, buddy):
		self.add(buddy)

	def __buddy_left_cb(self, activity, buddy):
		self.remove(buddy)

	def __buddy_clicked_cb(self, icon, buddy):
		self._friends.add_buddy(buddy)

class ActionsBar(goocanvas.Group):
	def __init__(self, shell, width):
		goocanvas.Group.__init__(self)
		self._width = width
		self._shell = shell

		self._y = 0

		icon = IconItem(icon_name='stock-share', size=self._width)
		icon.connect('clicked', self.__share_clicked_cb)
		self.add_icon(icon)

		icon = IconItem(icon_name='stock-invite', size=self._width)
		icon.connect('clicked', self.__invite_clicked_cb)
		self.add_icon(icon)

		icon = IconItem(icon_name='stock-chat', size=self._width)
		icon.connect('clicked', self.__chat_clicked_cb)
		self.add_icon(icon)

	def add_icon(self, icon):
		icon.set_property('y', self._y)
		self._y += (self._width + 6)
		self.add_child(icon)		

	def __share_clicked_cb(self, item):
		activity = self._shell.get_current_activity()
		if activity != None:
			activity.share()

	def __invite_clicked_cb(self, item):
		pass

	def __chat_clicked_cb(self, item):
		pass
