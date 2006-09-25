from sugar.presence import PresenceService
from sugar.canvas.IconColor import IconColor
import gobject

_NOT_PRESENT_COLOR = "#888888,#BBBBBB"

class BuddyModel(gobject.GObject):
	__gsignals__ = {
		'appeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
		'disappeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
		'color-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([gobject.TYPE_PYOBJECT])),
		'icon-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([])),
		'current-activity-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
									([gobject.TYPE_PYOBJECT]))
	}

	def __init__(self, name=None, buddy=None):
		if name and buddy:
			raise RuntimeError("Must specify only _one_ of name or buddy.")

		gobject.GObject.__init__(self)

		self._ba_handler = None
		self._pc_handler = None
		self._dis_handler = None
		self._bic_handler = None

		self._cur_activity = None
		self._pservice = PresenceService.get_instance()

		self._buddy = None

		# If given just a name, try to get the buddy from the PS first
		if not buddy:
			self._name = name
			# FIXME: use public key, not name
			buddy = self._pservice.get_buddy_by_name(self._name)

		# If successful, copy properties from the PS buddy object
		if buddy:
			self.__update_buddy(buddy)
		else:
			# Otherwise, connect to the PS's buddy-appeared signal and
			# wait for the buddy to appear
			self._ba_handler = self._pservice.connect('buddy-appeared',
					self.__buddy_appeared_cb)
			self._name = name
			# Set color to 'inactive'/'disconnected'
			self.__set_color_from_string(_NOT_PRESENT_COLOR)

	def __set_color_from_string(self, color_string):
		self._color = IconColor(color_string)

	def get_name(self):
		return self._name

	def get_color(self):
		return self._color

	def get_buddy(self):
		return self._buddy

	def get_current_activity(self):
		return self._cur_activity

	def __update_buddy(self, buddy):
		if not buddy:
			raise ValueError("Buddy cannot be None.")

		self._buddy = buddy
		self._name = self._buddy.get_name()
		self.__set_color_from_string(self._buddy.get_color())

		self._pc_handler = self._buddy.connect('property-changed', self.__buddy_property_changed_cb)
		self._dis_handler = self._buddy.connect('disappeared', self.__buddy_disappeared_cb)
		self._bic_handler = self._buddy.connect('icon-changed', self.__buddy_icon_changed_cb)

	def __buddy_appeared_cb(self, pservice, buddy):
		# FIXME: use public key rather than buddy name
		if self._buddy or buddy.get_name() != self._name:
			return

		if self._ba_handler:
			# Once we have the buddy, we no longer need to
			# monitor buddy-appeared events
			self._pservice.disconnect(self._ba_handler)
			self._ba_handler = None

		self.__update_buddy(buddy)
		self.emit('appeared')

	def __buddy_property_changed_cb(self, buddy, keys):
		if not self._buddy:
			return

		# all we care about right now is current activity
		if 'curact' in keys:
			curact = self._buddy.get_current_activity()
			self._cur_activity = self._pservice.get_activity(curact)
			self.emit('current-activity-changed', self._cur_activity)
		if 'color' in keys:
			self.__set_color_from_string(self._buddy.get_color())
			self.emit('color-changed', self.get_color())

	def __buddy_disappeared_cb(self, buddy):
		if buddy != self._buddy:
			return
		self._buddy.disconnect(self._pc_handler)
		self._buddy.disconnect(self._dis_handler)
		self._buddy.disconnect(self._bic_handler)
		self.__set_color_from_string(_NOT_PRESENT_COLOR)
		self._cur_activity = None
		self.emit('current-activity-changed', self._cur_activity)
		self.emit('disappeared')
		self._buddy = None

	def __buddy_icon_changed_cb(self, buddy):
		self.emit('icon-changed')
