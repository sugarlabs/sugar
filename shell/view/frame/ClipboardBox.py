import logging
import dbus
import hippo

from sugar.graphics import style
from view.ClipboardIcon import ClipboardIcon

class ClipboardBox(hippo.CanvasBox):

	_CLIPBOARD_SERVICE = "org.laptop.Clipboard"
	_CLIPBOARD_OBJECT_PATH = "/org/laptop/Clipboard"
	
	def __init__(self, shell, menu_shell):
		hippo.CanvasBox.__init__(self)
		self._shell = shell
		self._menu_shell = menu_shell
		self._icons = {}

		bus = dbus.SessionBus()
		bus.add_signal_receiver(self.name_owner_changed_cb,
									signal_name="NameOwnerChanged",
									dbus_interface="org.freedesktop.DBus")
		# Try to register to ClipboardService, if we fail, we'll try later.
		try:
			self._connect_clipboard_signals()
		except dbus.DBusException, exception:
			pass
		
	def _connect_clipboard_signals(self):
		bus = dbus.SessionBus()
		proxy_obj = bus.get_object(self._CLIPBOARD_SERVICE, self._CLIPBOARD_OBJECT_PATH)
		iface = dbus.Interface(proxy_obj, self._CLIPBOARD_SERVICE)
		iface.connect_to_signal('object_added', self.object_added_callback)	
		iface.connect_to_signal('object_deleted', self.object_deleted_callback)
		iface.connect_to_signal('object_state_updated', self.object_state_updated_callback)	

	def name_owner_changed_cb(self, name, old, new):
		if name != self._CLIPBOARD_SERVICE:
			return
		if (not old and not len(old)) and (new and len(new)):
			# ClipboardService started up
			self._connect_clipboard_signals()

	def object_added_callback(self, mimeType, fileName):
		icon = ClipboardIcon(self._menu_shell, fileName)
		style.apply_stylesheet(icon, 'frame.BuddyIcon')
		self.append(icon)
		self._icons[fileName] = icon
		
		logging.debug('ClipboardBox: ' + fileName + ' was added.')

	def object_deleted_callback(self, fileName):
		icon = self._icons[fileName]
		self.remove(icon)
		self._icons.remove(icon)		
		logging.debug('ClipboardBox: ' + fileName + ' was deleted.')

	def object_state_updated_callback(self, fileName, percent):
		icon = self._icons[fileName]
		icon.set_percent(percent)
		logging.debug('ClipboardBox: ' + fileName + ' state was updated.')
