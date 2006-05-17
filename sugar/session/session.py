import os
import sys

import pygtk
pygtk.require('2.0')
import gtk

from sugar.shell import shell

def start(console):
	shell.main()
	print 'aaaa'
	activities = ['sugar/chat/chat', 'sugar/browser/browser']

	for activity in activities:
		args = [ 'python', '-m', activity ]
		if console:
			args.append('--console')
		os.spawnvp(os.P_NOWAIT, 'python', args)

	gtk.main()
