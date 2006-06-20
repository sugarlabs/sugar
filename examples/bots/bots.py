import os

import pygtk
pygtk.require('2.0')
import gtk

from sugar.bots import Bot

basedir = os.path.dirname(__file__)

bot = Bot("Chaitanya", os.path.join(basedir, "chaitanya.jpg"))
bot.start()

bot = Bot("Kiu", os.path.join(basedir, "kiu.jpg"))
bot.start()

bot = Bot("Penelope", os.path.join(basedir, "penelope.jpg"))
bot.start()

gtk.main()
