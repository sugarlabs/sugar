#!/usr/bin/python

from sugar.simulator import Bot
from sugar.simulator import ShareActivityAction
from sugar.graphics.iconcolor import IconColor
import os, random, gobject

class KiuBot(Bot):
	def __init__(self):
		Bot.__init__(self, 'kiu', IconColor('#5E4505,#0F8A0F'))
		self._olpc_chat_service = None
		self._web_activity_service = None
		self._activity_switch_timeout = None
		self._curact = None

		action = ShareActivityAction('OLPC channel',
							 '_GroupChatActivity_Sugar_redhat_com._udp',
							 self.__share_olpc_chat_cb)
		self.add_action(action, 10)

		action = ShareActivityAction('All About Giraffes',
							 '_BrowserActivity_Sugar_redhat_com._udp',
							 self.__share_web_activity_cb)
		self.add_action(action, 20)

		curdir = os.path.abspath(os.path.dirname(__file__))
		self._icon_file = os.path.join(curdir, 'kiu.jpg')

	def __activity_switch_cb(self):
		self._activity_switch_timeout = None
		which = random.randint(1, 2)
		if which == 1:
			actid = self._olpc_chat_activity.get_id()
		elif which == 2:
			actid = self._web_activity.get_id()
		else:
			raise RuntimeError("WTF? unexpected value")
		if actid != self._curact:
			print "KIU: now setting current activity to %s" % actid
			self._owner.set_current_activity(actid)
			self._curact = actid
		self._schedule_activity_switch_timeout()
		return False

	def _schedule_activity_switch_timeout(self):
		if self._activity_switch_timeout:
			return
		interval = random.randint(10000, 20000)
		self._activity_switch_timeout = gobject.timeout_add(interval,
				self.__activity_switch_cb)

	def __share_olpc_chat_cb(self, sim_activity, service):
		self._olpc_chat_service = service
		self._olpc_chat_activity = sim_activity
		self._schedule_activity_switch_timeout()

	def __share_web_activity_cb(self, sim_activity, service):
		self._web_activity_service = service
		self._web_activity = sim_activity
		self._schedule_activity_switch_timeout()

def main():
	bot = KiuBot()
	bot.start()


if __name__ == "__main__":
	main()
