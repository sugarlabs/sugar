# Copyright (C) 2006, Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

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
