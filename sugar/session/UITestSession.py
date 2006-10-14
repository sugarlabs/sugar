# Copyright (C) 2006, Red Hat, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import os

from sugar.session.DbusProcess import DbusProcess
from sugar.session.MatchboxProcess import MatchboxProcess
from sugar.session.Emulator import Emulator
from sugar import env

class UITestSession:
	def start(self):
		env.setup_python_path()

		if os.environ.has_key('SUGAR_EMULATOR') and \
		   os.environ['SUGAR_EMULATOR'] == 'yes':
			emulator = Emulator()
			emulator.start()

		process = MatchboxProcess()
		process.start()

		process = DbusProcess()
		process.start()
