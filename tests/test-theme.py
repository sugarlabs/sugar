#!/usr/bin/python
import pygtk
pygtk.require('2.0')

from sugar.session.UITestSession import UITestSession

session = UITestSession()
session.start()

import gtk

# Main window
window = gtk.Window()
window.connect("destroy", lambda w: gtk.main_quit())
#window.set_border_width(10)

# Main VBox

main_vbox = gtk.VBox(homogeneous=False, spacing=0)
window.add(main_vbox)

###############################           ##############################
###############################   Menus   ##############################
###############################           ##############################

menu = gtk.Menu()
file_menu = gtk.Menu()    # Don't need to show menus
edit_menu = gtk.Menu()

# Create the menu items
dummy_item_1 = gtk.MenuItem("Dummy Item 1")
dummy_item_2 = gtk.MenuItem("Dummy Item 2")
quit_item = gtk.MenuItem("Quit")
dummy_item_3 = gtk.MenuItem("Dummy Item 3")
dummy_item_4 = gtk.MenuItem("Dummy Item 4")
dummy_item_5 = gtk.MenuItem("Dummy Item 5")

# Add them to the menu
file_menu.append(dummy_item_1)
file_menu.append(dummy_item_2)
file_menu.append(quit_item)

edit_menu.append(dummy_item_3)
edit_menu.append(dummy_item_4)
edit_menu.append(dummy_item_5)

# We can attach the Quit menu item to our exit function
quit_item.connect_object ("activate", lambda w: gtk.main_quit (), "file.quit")

# We do need to show menu items
dummy_item_1.show()
dummy_item_2.show()
quit_item.show()
dummy_item_3.show()
dummy_item_4.show()
dummy_item_5.show()

# Pack the menu into the menubar
menu_bar = gtk.MenuBar()
main_vbox.pack_start(menu_bar, False, False, 0)
menu_bar.show()

file_item = gtk.MenuItem("File")
file_item.show()
menu_bar.append(file_item)
file_item.set_submenu(file_menu)

edit_item = gtk.MenuItem("Edit")
edit_item.show()
menu_bar.append(edit_item)
edit_item.set_submenu(edit_menu)


# Scrolled window
scrolled_window = gtk.ScrolledWindow(hadjustment=None, vadjustment=None)
#scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
scrolled_window.set_border_width(10)
main_vbox.pack_start(scrolled_window, True, True, 0)

# Vbox inside the scrolled window
vbox = gtk.VBox(homogeneous=False, spacing=10)
scrolled_window.add_with_viewport(vbox)
vbox.set_border_width (10)

# Label
label = gtk.Label("This is a label")
vbox.pack_start(label, False, False, 0)

# Entry
entry = gtk.Entry ()
entry.set_text("Type some text here")
vbox.pack_start(entry, False, False, 0)

# Buttons
buttons_hbox = gtk.HBox(homogeneous=False, spacing=5)
vbox.pack_start(buttons_hbox, False, False, 0)

button_1 = gtk.Button ("Button 1")
buttons_hbox.pack_start(button_1, False, False, 0)

button_2 = gtk.Button ("Button 2")
buttons_hbox.pack_start(button_2, False, False, 0)

button_3 = gtk.Button ("Button 3")
buttons_hbox.pack_start(button_3, False, False, 0)

window.show_all()

gtk.main()
