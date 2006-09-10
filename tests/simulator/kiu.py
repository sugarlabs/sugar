#!/usr/bin/python

from sugar.simulator import Bot
from sugar.simulator import ShareActivityAction
from sugar.canvas.IconColor import IconColor

bot = Bot('kiu', IconColor('#5E4505,#0F8A0F'))

action = ShareActivityAction('OLPC channel',
							 '_GroupChatActivity_Sugar_redhat_com._udp')
bot.add_action(action, 10)

action = ShareActivityAction('Sugar channel',
							 '_GroupChatActivity_Sugar_redhat_com._udp')
bot.add_action(action, 20)

bot.start()
