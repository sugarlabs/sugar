#!/usr/bin/python

from sugar.simulator import Bot
from sugar.simulator import ShareActivityAction
from sugar.canvas.IconColor import IconColor
import os, random, gobject

class KiuBot(Bot):
	def __init__(self):
		Bot.__init__(self, 'kiu', IconColor('#5E4505,#0F8A0F'))
		self._olpc_channel_service = None
		self._sugar_channel_service = None
		self._activity_switch_timeout = None
		self._curact = None

		action = ShareActivityAction('OLPC channel',
							 '_GroupChatActivity_Sugar_redhat_com._udp',
							 self.__share_olpc_channel_cb)
		self.add_action(action, 10)

		action = ShareActivityAction('Sugar channel',
							 '_GroupChatActivity_Sugar_redhat_com._udp',
							 self.__share_sugar_channel_cb)
		self.add_action(action, 20)

		self._icon_file = os.path.abspath("kiu.jpg")

	def __activity_switch_cb(self):
		self._activity_switch_timeout = None
		which = random.randint(1, 2)
		if which == 1:
			actid = self._olpc_channel_activity.get_id()
		elif which == 2:
			actid = self._sugar_channel_activity.get_id()
		else:
			raise RuntimeError("WTF? unexpected value")
		if actid != self._curact:
			print "KIU: now setting current activity to %s" % actid
			self._owner.set_current_activity(actid)
			self._schedule_activity_switch_timeout()
			self._curact = actid
		return False

	def _schedule_activity_switch_timeout(self):
		if self._activity_switch_timeout:
			return
		interval = random.randint(10000, 20000)
		self._activity_switch_timeout = gobject.timeout_add(interval,
				self.__activity_switch_cb)

	def __share_olpc_channel_cb(self, sim_activity, service):
		self._olpc_channel_service = service
		self._olpc_channel_activity = sim_activity
		self._schedule_activity_switch_timeout()

	def __share_sugar_channel_cb(self, sim_activity, service):
		self._sugar_channel_service = service
		self._sugar_channel_activity = sim_activity
		self._schedule_activity_switch_timeout()

def main():
	bot = KiuBot()
	bot.start()


if __name__ == "__main__":
	main()
