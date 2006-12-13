from sugar.graphics.menuicon import MenuIcon
from view.clipboardmenu import ClipboardMenu
from sugar.activity import ActivityFactory
from sugar.clipboard import clipboardservice

class ClipboardIcon(MenuIcon):

    def __init__(self, menu_shell, object_id, name):
        MenuIcon.__init__(self, menu_shell, icon_name='activity-xbook')
        self._object_id = object_id
        self._name = name
        self._percent = 0
        self.connect('activated', self._icon_activated_cb)
        self._menu = None
        
    def create_menu(self):
        self._menu = ClipboardMenu(self._name, self._percent)
        self._menu.connect('action', self._popup_action_cb)
        return self._menu

    def set_percent(self, percent):
        self._percent = percent
        if self._menu:
            self._menu.set_percent(percent)

    def _icon_activated_cb(self, icon):
        if self._percent == 100:
            cb_service = clipboardservice.get_instance()
            format_types = cb_service.get_object_format_types(self._object_id)
            if len(format_types) > 0 and format_types[0] == "application/pdf":
                activity = ActivityFactory.create("org.laptop.sugar.Xbook")
                activity.execute("open_document", [self._object_id])

    def _popup_action_cb(self, popup, action):
        self.popdown()
        
        if action == ClipboardMenu.ACTION_STOP_DOWNLOAD:
            raise "Stopping downloads still not implemented."
        elif action == ClipboardMenu.ACTION_DELETE:
            cb_service = clipboardservice.get_instance()
            cb_service.delete_object(self._object_id)

    def get_object_id(self):
        return self._object_id
