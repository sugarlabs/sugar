import gtk
import dbus

from WindowManager import WindowManager
from ActivityContainer import ActivityContainer

class ConsoleLogger(dbus.service.Object):
	def __init__(self):
		session_bus = dbus.SessionBus()
		bus_name = dbus.service.BusName('com.redhat.Sugar.Logger', bus=session_bus)
		object_path = '/com/redhat/Sugar/Logger'
		dbus.service.Object.__init__(self, bus_name, object_path)

		self._window = gtk.Window()
		self._window.set_title("Console")
		self._window.connect("delete_event", lambda w, e: w.hide_on_delete())

		self._nb = gtk.Notebook()
		self._window.add(self._nb)
		self._nb.show()
				
		self._consoles = {}

		console_wm = WindowManager(self._window)		
		console_wm.set_type(WindowManager.TYPE_POPUP)
		console_wm.set_geometry(0.1, 0.1, 0.8, 0.8)
		console_wm.set_key(gtk.keysyms.F3)

	def _create_console(self, application):
		sw = gtk.ScrolledWindow()
		sw.set_policy(gtk.POLICY_AUTOMATIC,
					  gtk.POLICY_AUTOMATIC)
		
		console = gtk.TextView()
		console.set_wrap_mode(gtk.WRAP_WORD)
		
		sw.add(console)
		console.show()
		
		self._nb.append_page(sw, gtk.Label(application))
		sw.show()
		
		return console

	@dbus.service.method('com.redhat.Sugar.Logger')
	def log(self, application, message):
		if self._consoles.has_key(application):
			console = self._consoles[application]
		else:
			console = self._create_console(application)
			self._consoles[application] = console
	
		buf = console.get_buffer() 
		buf.insert(buf.get_end_iter(), message)

