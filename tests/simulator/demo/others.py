from sugar.simulator import Bot

for i in range(0, 10):
	bot = Bot()

	bot.wait(20)
	bot.join_activity('giraffes')
	bot.change_activity('giraffes')

	bot.start()
