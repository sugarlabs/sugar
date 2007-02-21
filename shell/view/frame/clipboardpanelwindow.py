import logging
import gtk
import hippo

from view.frame.PanelWindow import PanelWindow
from view.frame.clipboardbox import ClipboardBox
from sugar.clipboard import clipboardservice
from sugar import util

class ClipboardPanelWindow(PanelWindow):
    def __init__(self, frame, orientation):
        PanelWindow.__init__(self, orientation)

        self._frame = frame

        # Listening for new clipboard objects
        clipboard = gtk.Clipboard()
        clipboard.connect("owner-change", self._owner_change_cb)

        root = self.get_root()

        box = ClipboardBox(frame.get_popup_context())
        root.append(box)

        # Receiving dnd drops
        self.drag_dest_set(0, [], 0)
        self.connect("drag_motion", box.drag_motion_cb)
        self.connect("drag_drop", box.drag_drop_cb)
        self.connect("drag_data_received", box.drag_data_received_cb)
        
        # Offering dnd drags
        self.drag_source_set(0, [], 0)
        self.add_events(gtk.gdk.BUTTON_PRESS_MASK |
                        gtk.gdk.POINTER_MOTION_HINT_MASK)
        self.connect("motion_notify_event", box.motion_notify_event_cb)
        self.get_canvas().connect("button_press_event", box.button_press_event_cb)
        self.connect("drag_end", box.drag_end_cb)
        self.connect("drag_data_get", box.drag_data_get_cb)

    def _owner_change_cb(self, clipboard, event):
        logging.debug("owner_change_cb")
        
        key = util.unique_id()
        
        cb_service = clipboardservice.get_instance()
        cb_service.add_object(key, name="")
        cb_service.set_object_percent(key, percent = 100)
        
        targets = clipboard.wait_for_targets()
        for target in targets:
            if target not in ('TIMESTAMP', 'TARGETS', 'MULTIPLE'):
                selection = clipboard.wait_for_contents(target)
                if selection:
                    self._add_selection(key, selection)
        
        self._frame.show_and_hide(0)

    def _add_selection(self, key, selection):
        if selection.data:
            logging.debug('adding type ' + selection.type + '.')
                        
            cb_service = clipboardservice.get_instance()
            cb_service.add_object_format(key, 
                                  selection.type,
                                  selection.data,
                                  on_disk = False)
