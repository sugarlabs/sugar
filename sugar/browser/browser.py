#!/usr/bin/env python

import pygtk
pygtk.require('2.0')
import gtk

import sugar.env

from sugar.session.LogWriter import LogWriter
from sugar.browser.BrowserShell import BrowserShell

log_writer = LogWriter("Web")
log_writer.start()

gtk.rc_parse(sugar.env.get_data_file('browser.rc'))

BrowserShell.get_instance().open_web_activity()

gtk.main()
