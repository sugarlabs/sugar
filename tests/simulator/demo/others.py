from sugar.simulator import Bot

for i in range(0, 10):
	bot = Bot()

	bot.wait(5)
	bot.change_activity('giraffes')

	bot.start()
