import gtk

from sugar.activity import Activity

class NewActivityButton(gtk.Button):
	def __init__(self):
		gtk.Button.__init__(self)

		hbox = gtk.HBox(False, 6)
		
		label = gtk.Label("New Activity")
		hbox.pack_start(label)
		label.show()
		
		arrow = gtk.Arrow(gtk.ARROW_DOWN, gtk.SHADOW_NONE)
		hbox.pack_start(arrow)
		arrow.show()

		self.set_image(hbox)

		self.connect("clicked", self.__clicked_cb)
	
	def __clicked_cb(self, button):
		print Activity.list_activities

class Toolbar(gtk.HBox):
	def __init__(self):
		gtk.HBox.__init__(self)
		
		new_activity_button = NewActivityButton()
		self.pack_start(new_activity_button)
		new_activity_button.show()

class HomeWindow(gtk.Window):
	def __init__(self):
		gtk.Window.__init__(self)
	
		vbox = gtk.VBox()

		toolbar = Toolbar()		
		vbox.pack_start(toolbar)
		toolbar.show()
		
		self.add(vbox)
		
