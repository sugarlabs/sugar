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

import gtk
import vte
import pango

from sugar.activity.Activity import Activity

_TERMINAL_ACTIVITY_TYPE = "_terminal._tcp"

class Terminal(gtk.HBox):
	def __init__(self):
		gtk.HBox.__init__(self, False, 4)

		self._vte = vte.Terminal()
		self._configure_vte()
		self._vte.set_size(30, 5)
		self._vte.set_size_request(200, 50)
		self._vte.show()
		self.pack_start(self._vte)
		
		self._scrollbar = gtk.VScrollbar(self._vte.get_adjustment())
		self._scrollbar.show()
		self.pack_start(self._scrollbar, False, False, 0)
		
		self._vte.connect("child-exited", lambda term: term.fork_command())

		self._vte.fork_command()

	def _configure_vte(self):
		self._vte.set_font(pango.FontDescription('Monospace 10'))
		self._vte.set_colors(gtk.gdk.color_parse ('#AAAAAA'),
							 gtk.gdk.color_parse ('#000000'),
							 [])
		self._vte.set_cursor_blinks(False)
		self._vte.set_audible_bell(False)
		self._vte.set_scrollback_lines(100)
		self._vte.set_allow_bold(True)
		self._vte.set_scroll_on_keystroke(False)
		self._vte.set_scroll_on_output(False)
		self._vte.set_emulation('xterm')
		self._vte.set_visible_bell(False)

	def on_gconf_notification(self, client, cnxn_id, entry, what):
		self.reconfigure_vte()

	def on_vte_button_press(self, term, event):
		if event.button == 3:
			self.do_popup(event)
			return True

	def on_vte_popup_menu(self, term):
		pass

class TerminalActivity(Activity):
	def __init__(self):
		Activity.__init__(self)
	
		self.set_title("Terminal")

		terminal = Terminal()
		self.add(terminal)
		terminal.show()
