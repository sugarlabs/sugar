#!/usr/bin/python

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

import os

import pygtk
pygtk.require('2.0')
import gtk
import gobject

from sugar import env

class LogBuffer(gtk.TextBuffer):
	def __init__(self, logfile):
		gtk.TextBuffer.__init__(self)

		self._logfile = logfile
		self._pos = 0

		self.update()

	def update(self):
		f = open(self._logfile, 'r')

		f.seek(self._pos)
		self.insert(self.get_end_iter(), f.read())
		self._pos = f.tell()

		f.close()

		return True

class LogView(gtk.ScrolledWindow):
	def __init__(self, model):
		gtk.ScrolledWindow.__init__(self)

		self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

		textview = gtk.TextView(model)
		textview.set_wrap_mode(gtk.WRAP_WORD)
		textview.set_editable(False)

		self.add(textview)
		textview.show()

class MultiLogView(gtk.Notebook):
	def __init__(self, path):
		gtk.Notebook.__init__(self)

		self._logs_path = path
		self._pages = {}

		self._update()

		gobject.timeout_add(1000, self._update)

	def _add_page(self, logfile):
		full_log_path = os.path.join(self._logs_path, logfile)
		model = LogBuffer(full_log_path)

		view = LogView(model)
		self.append_page(view, gtk.Label(logfile))
		view.show()

		self._pages[logfile] = model

	def _update(self):
		if not os.path.isdir(self._logs_path):
			return True

		for logfile in os.listdir(self._logs_path):
			if self._pages.has_key(logfile):
				self._pages[logfile].update()
			else:
				self._add_page(logfile)

		return True

class Interface:

	def __init__(self):
		path = os.path.join(env.get_profile_path(), 'logs')
		viewer = MultiLogView(path)
		viewer.show()
		self.widget = viewer
		