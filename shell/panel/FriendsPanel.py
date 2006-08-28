import goocanvas

from panel.Panel import Panel
from sugar.canvas.IconItem import IconItem
from sugar.canvas.IconColor import IconColor
from sugar.presence import PresenceService

class BuddyIcon(IconItem):
	def __init__(self, buddy, **kwargs):
		IconItem.__init__(self, icon_name='stock-buddy',
						  color=buddy.get_color(), **kwargs)

class FriendsGroup(goocanvas.Group):
	def __init__(self, shell, width):
		goocanvas.Group.__init__(self)

		i = 0
		while i < 10:
			icon = IconItem(icon_name='stock-buddy',
							color=IconColor('white'),
							y=i * (width + 6), size=width)
			self.add_child(icon)
			i += 1

		shell.connect('activity-changed', self.__activity_changed_cb)

	def __activity_changed_cb(self, group, activity):
		print 'Changed'

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

class FriendsPanel(Panel):
	def __init__(self, shell):
		Panel.__init__(self)
		self._shell = shell

	def construct(self):
		Panel.construct(self)

		root = self.get_root()

		actions_bar = ActionsBar(self._shell, self.get_width())
		root.add_child(actions_bar)

		friends_group = FriendsGroup(self._shell, self.get_width())
		friends_group.translate(0, 150)
		root.add_child(friends_group)		
