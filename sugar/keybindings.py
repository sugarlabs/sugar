import gtk
import dbus

# FIXME These should be handled by the wm, but it's incovenient
# to do that with matchbox at the moment

def setup_global_keys(window, shell = None):
	if not shell:
		bus = dbus.SessionBus()
		proxy_obj = bus.get_object('com.redhat.Sugar.Shell', '/com/redhat/Sugar/Shell')
		shell = dbus.Interface(proxy_obj, 'com.redhat.Sugar.Shell')

	window.connect("key-press-event", __key_press_event_cb, shell)

def __key_press_event_cb(window, event, shell):
	if event.keyval == gtk.keysyms.F2:
		shell.toggle_people()
	if event.keyval == gtk.keysyms.F3:
		shell.toggle_console()
