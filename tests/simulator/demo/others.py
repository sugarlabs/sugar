import random

from sugar.simulator import Bot

for i in range(0, 8):
	bot = Bot()

	bot.wait(random.randint(10, 20))
	bot.join_activity('giraffes')
	bot.change_activity('giraffes')

	bot.start()

for i in range(0, 6):
	bot = Bot()

	bot.wait(random.randint(10, 20))
	bot.join_activity('nekkhamma')
	bot.change_activity('nekkhamma')

	bot.start()
