import logging
import dbus
import hippo

from sugar.graphics import style
from view.ClipboardIcon import ClipboardIcon
from sugar.clipboard import ClipboardService

class ClipboardBox(hippo.CanvasBox):
	
	def __init__(self, frame, menu_shell):
		hippo.CanvasBox.__init__(self)
		self._frame = frame
		self._menu_shell = menu_shell
		self._icons = {}
		
		cb_service = ClipboardService.get_instance()
		cb_service.connect('object-added', self._object_added_cb)
		cb_service.connect('object-deleted', self._object_deleted_cb)
		cb_service.connect('object-state-changed', self._object_state_changed_cb)

	def _object_added_cb(self, cb_service, name, mimeType, fileName):
		icon = ClipboardIcon(self._menu_shell, name, fileName)
		style.apply_stylesheet(icon, 'frame.BuddyIcon')
		self.append(icon)
		self._icons[fileName] = icon
		
		if not self._frame.is_visible():
			self._frame.show_and_hide(0.1)
		
		logging.debug('ClipboardBox: ' + fileName + ' was added.')

	def _object_deleted_cb(self, cb_service, fileName):
		icon = self._icons[fileName]
		self.remove(icon)
		del self._icons[fileName]
		logging.debug('ClipboardBox: ' + fileName + ' was deleted.')

	def _object_state_changed_cb(self, cb_service, fileName, percent):
		icon = self._icons[fileName]
		icon.set_percent(percent)
		logging.debug('ClipboardBox: ' + fileName + ' state was changed.')
