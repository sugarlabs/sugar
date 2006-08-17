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
