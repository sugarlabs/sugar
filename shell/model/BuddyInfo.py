from sugar.presence import PresenceService
from sugar.canvas.IconColor import IconColor

class BuddyInfo:
	def __init__(self, buddy=None):
		if buddy:
			self.set_name(buddy.get_name())
			self.set_color(buddy.get_color())

	def set_name(self, name):
		self._name = name

	def set_color(self, color_string):
		self._color = IconColor(color_string)

	def get_name(self):
		return self._name

	def get_color(self):
		return self._color

	def get_buddy(self):
		pservice = PresenceService.get_instance()
		return pservice.get_buddy_by_name(self._name)
