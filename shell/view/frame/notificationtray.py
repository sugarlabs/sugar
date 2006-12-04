import gtk

from _sugar import TrayManager

class NotificationTray(gtk.HBox):
    def __init__(self):
        gtk.HBox.__init__(self)

        self._manager = TrayManager()
        self._manager.connect('tray-icon-added', self._icon_added_cb)
        self._manager.connect('tray-icon-removed', self._icon_removed_cb)
        self._manager.manage_screen(gtk.gdk.screen_get_default())

    def _icon_added_cb(self, manager, icon):
        self.pack_start(icon, False)

    def _icon_removed_cb(self, manager, icon):
        icon.destroy()
