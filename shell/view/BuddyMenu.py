from sugar.canvas.Menu import Menu
from sugar.canvas.IconItem import IconItem
from sugar.presence import PresenceService
import gtk
import goocanvas

_ICON_SIZE = 75

class BuddyMenu(Menu):
	ACTION_MAKE_FRIEND = 0
	ACTION_INVITE = 1
	ACTION_REMOVE_FRIEND = 2

	def __init__(self, shell, buddy):
		Menu.__init__(self, shell.get_grid(), buddy.get_name())

		self._buddy = buddy
		self._buddy.connect('icon-changed', self.__buddy_icon_changed_cb)
		self._shell = shell

		owner = shell.get_model().get_owner()
		if buddy.get_name() != owner.get_name():
			self._add_actions()

	def _get_buddy_icon_pixbuf(self):
		buddy_object = self._buddy.get_buddy()
		if not buddy_object:
			return None
		icon_data = buddy_object.get_icon()
		icon_data_string = ""
		for item in icon_data:
			if item < 0:
				item = item + 128
			icon_data_string = icon_data_string + chr(item)
		pbl = gtk.gdk.PixbufLoader()
		pbl.write(icon_data_string)
		pbl.close()
		pixbuf = pbl.get_pixbuf()
		del pbl
		return pixbuf

	def _add_actions(self):
		shell_model = self._shell.get_model()
		pservice = PresenceService.get_instance()

		pixbuf = self._get_buddy_icon_pixbuf()
		if pixbuf:
			scaled_pixbuf = pixbuf.scale_simple(_ICON_SIZE, _ICON_SIZE, gtk.gdk.INTERP_BILINEAR)
			del pixbuf
			self._buddy_icon_item = goocanvas.Image()
			self._buddy_icon_item.set_property('pixbuf', scaled_pixbuf)
			self.add_image(self._buddy_icon_item, 5, 5)

		friends = shell_model.get_friends()
		if friends.has_buddy(self._buddy):
			icon = IconItem(icon_name='stock-remove-friend')
			self.add_action(icon, BuddyMenu.ACTION_REMOVE_FRIEND) 
		else:
			icon = IconItem(icon_name='stock-make-friend')
			self.add_action(icon, BuddyMenu.ACTION_MAKE_FRIEND)

		icon = IconItem(icon_name='stock-chat')
		self.add_action(icon, -1)

		activity_id = shell_model.get_current_activity()
		if activity_id != None:
			activity_ps = pservice.get_activity(activity_id)

			# FIXME check that the buddy is not in the activity already

			icon = IconItem(icon_name='stock-invite')
			self.add_action(icon, BuddyMenu.ACTION_INVITE)

	def __buddy_icon_changed_cb(self, buddy):
		pass

