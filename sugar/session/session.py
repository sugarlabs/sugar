import os
import sys

import pygtk
pygtk.require('2.0')
import gtk

from sugar.shell import shell

def start():
	shell.main()

	activities = ['sugar/chat/chat', 'sugar/browser/browser']

	for activity in activities:
		os.spawnvp(os.P_NOWAIT, 'python', [ 'python', '-m', activity ])

	gtk.main()
