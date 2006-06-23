import os

import gtk
import vte

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
class TerminalActivity(Activity):
	def __init__(self):
		Activity.__init__(self, _TERMINAL_ACTIVITY_TYPE)
	
	def on_connected_to_shell(self):
		self.set_tab_text("Terminal")

		plug = self.gtk_plug()		

		terminal = Terminal()
		plug.add(terminal)
		terminal.show()

		plug.show()
		
activity = TerminalActivity()
activity.connect_to_shell()

gtk.main()
