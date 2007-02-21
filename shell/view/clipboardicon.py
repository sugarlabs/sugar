import logging

from sugar.graphics.canvasicon import CanvasIcon
from view.clipboardmenu import ClipboardMenu
from sugar.graphics.iconcolor import IconColor
from sugar.activity import activityfactory
from sugar.clipboard import clipboardservice
from sugar import util

class ClipboardIcon(CanvasIcon):

    def __init__(self, popup_context, object_id, name):
        CanvasIcon.__init__(self)
        self._popup_context = popup_context
        self._object_id = object_id
        self._name = name
        self._percent = 0
        self._preview = None
        self._activity = None
        self.connect('activated', self._icon_activated_cb)
        self._menu = None
        
    def get_popup(self):
        self._menu = ClipboardMenu(self._name, self._percent, self._preview,
                                   self._activity)
        self._menu.connect('action', self._popup_action_cb)
        return self._menu

    def get_popup_context(self):
        return self._popup_context

    def set_state(self, name, percent, icon_name, preview, activity):
        self._name = name
        self._percent = percent
        self._preview = preview
        self._activity = activity
        self.set_property("icon_name", icon_name)
        if self._menu:
            self._menu.set_state(name, percent, preview, activity)

        if activity and percent < 100:
            self.set_property('color', IconColor("#000000,#424242"))
        else:
            self.set_property('color', IconColor("#000000,#FFFFFF"))
    
    def _activity_create_success_cb(self, handler, activity):
        activity.start(util.unique_id())
        activity.execute("open_document", [self._object_id])

    def _activity_create_error_cb(self, handler, err):
        pass

    def _open_file(self):
        if self._percent < 100 or not self._activity:
            return

        logging.debug("_icon_activated_cb: " + self._object_id)

        # Launch the activity to handle this item
        handler = activityfactory.create(self._activity)
        handler.connect('success', self._activity_create_success_cb)
        handler.connect('error', self._activity_create_error_cb)

    def _icon_activated_cb(self, icon):
        self._open_file()
                        
    def _popup_action_cb(self, popup, menu_item):
        action = menu_item.props.action_id
        
        if action == ClipboardMenu.ACTION_STOP_DOWNLOAD:
            raise "Stopping downloads still not implemented."
        elif action == ClipboardMenu.ACTION_DELETE:
            cb_service = clipboardservice.get_instance()
            cb_service.delete_object(self._object_id)
        elif action == ClipboardMenu.ACTION_OPEN:
            self._open_file()
        
    def get_object_id(self):
        return self._object_id
