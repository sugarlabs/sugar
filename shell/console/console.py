#!/usr/bin/env python

import gtk

# Console interfaces
import memphis
import logviewer
import terminal

window = gtk.Window()
window.set_title('Developer console')

width = gtk.gdk.screen_width() * 95 / 100
height = gtk.gdk.screen_height() * 95 / 100

window.set_default_size(width, height)

window.realize()
window.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)

# Memphis interface
memphis_widget = memphis.Interface().widget
memphis_widget.show()

# Log viewer interface
logviewer_widget = logviewer.Interface().widget
logviewer_widget.show()

# Terminal interface
terminal_widget	= terminal.Interface().widget
terminal_widget.show()

# Notebook
notebook = gtk.Notebook()
notebook.append_page(memphis_widget, gtk.Label('Memphis'))
notebook.append_page(logviewer_widget, gtk.Label('Log Viewer'))
notebook.append_page(terminal_widget, gtk.Label('Terminal'))

notebook.show()

window.add(notebook)
window.show()
gtk.main()
