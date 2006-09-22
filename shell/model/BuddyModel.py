from sugar.presence import PresenceService
from sugar.canvas.IconColor import IconColor

class BuddyModel:
	def __init__(self, buddy=None):
		self._cur_activity = None
		self._pservice = PresenceService.get_instance()

		self._buddy = buddy
		if self._buddy:
			self.set_name(self._buddy.get_name())
			self.set_color(self._buddy.get_color())
			self._buddy.connect('property-changed',
					self.__buddy_property_changed_cb)
		else:
			# if we don't have a buddy yet, connect to the PS
			# and wait until the buddy pops up on the network
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
		# If we have a buddy already, just return
		if self._buddy:
			return self._buddy

		# Otherwise try to get the buddy from the PS
		self._buddy = self._pservice.get_buddy_by_name(self._name)
		if self._buddy:
			self._buddy.connect('property-changed',
					self.__buddy_property_changed_cb)
		return self._buddy

	def __buddy_appeared_cb(self, pservice, buddy):
		# FIXME: use public key rather than buddy name
		if not self._buddy and buddy.get_name() == self._name:
			self.get_buddy()

	def __buddy_property_changed_cb(self, buddy, keys):
		# all we care about right now is current activity
		curact = self._buddy.get_current_activity()
		self._cur_activity = self._pservice.get_activity(curact)

