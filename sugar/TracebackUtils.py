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

import sys
import traceback
import os
import signal

haveThreadframe = True
try:
	import threadframe
except ImportError:
	haveThreadframe = False

class TracebackHelper(object):
	def __init__(self):
		fname = "%s-%d" % (os.path.basename(sys.argv[0]), os.getpid())
		self._fpath = os.path.join("/tmp", fname)
		print "Tracebacks will be written to %s on SIGUSR1" % self._fpath
		signal.signal(signal.SIGUSR1, self._handler)

	def __del__(self):
		try:
			os.remove(self._fpath)
		except OSError:
			pass

	def _handler(self, signum, pframe):
		f = open(self._fpath, "a")
		if not haveThreadframe:
			f.write("Threadframe not installed.  No traceback available.\n")
		else:
			frames = threadframe.dict()
			for thread_id, frame in frames.iteritems():
				f.write(('-' * 79) + '\n')
				f.write('[Thread %s] %d' % (thread_id, sys.getrefcount(frame)) + '\n')
				traceback.print_stack(frame, limit=None, file=f)
				f.write("\n")
		f.write('\n')
		f.close()
