import gtk

from sugar.chat.ActivityChat import ActivityChat
from PresenceView import PresenceView

class PeopleWindow(gtk.Window):
	def __init__(self, shell, activity):
		gtk.Window.__init__(self)

		self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
		self.set_skip_taskbar_hint(True)
		self.set_decorated(False)
		self.set_default_size(620, 460)

		hbox = gtk.HBox(False, 12)
		hbox.set_border_width(12)

		presence_view = PresenceView(shell)
		presence_view.set_activity(activity)
		hbox.pack_start(presence_view, False)
		presence_view.show()

		chat = ActivityChat(activity)
		hbox.pack_start(chat)
		chat.show()

		self.add(hbox)
		hbox.show()
