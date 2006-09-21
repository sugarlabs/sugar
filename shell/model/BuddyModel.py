from sugar.presence import PresenceService
from sugar.canvas.IconColor import IconColor

class BuddyModel:
	def __init__(self, buddy=None):
		if buddy:
			self.set_name(buddy.get_name())
			self.set_color(buddy.get_color())
		self._buddy = buddy
		self._cur_activity = None
		self._pservice = PresenceService.get_instance()
		self._pservice.connect('buddy-appeared', self.__buddy_appeared_cb)

	def set_name(self, name):
		self._name = name

	def set_color(self, color_string):
		self._color = IconColor(color_string)

	def get_name(self):
		return self._name

	def get_color(self):
		return self._color

	def get_buddy(self):
		if not self._buddy:
			self._buddy = self._pservice.get_buddy_by_name(self._name)
			if self._buddy:
				self._buddy.connect('property-changed',
						self.__buddy_property_changed_cb)
		return self._buddy

	def __buddy_appeared_cb(self, pservice, buddy):
		if not self._buddy and buddy.get_name() == self._name:
			self.get_buddy()

	def __buddy_property_changed_cb(self, buddy, keys):
		curact = self._buddy.get_current_activity()
		self._cur_activity = self._pservice.get_activity(curact)

