import logging
import gtk
import hippo

from view.frame.framewindow import FrameWindow
from view.frame.clipboardbox import ClipboardBox
from sugar.clipboard import clipboardservice
from sugar import util

class ClipboardPanelWindow(FrameWindow):
    def __init__(self, frame, orientation):
        FrameWindow.__init__(self, orientation)

        self._frame = frame

        # Listening for new clipboard objects
        # NOTE: we need to keep a reference to gtk.Clipboard in order to keep
        # listening to it.
        self._clipboard = gtk.Clipboard()
        self._clipboard.connect("owner-change", self._owner_change_cb)

        root = self.get_root()

        self._clipboard_box = ClipboardBox(frame.get_popup_context())
        root.append(self._clipboard_box)

        # Receiving dnd drops
        self.drag_dest_set(0, [], 0)
        self.connect("drag_motion", self._clipboard_box.drag_motion_cb)
        self.connect("drag_drop", self._clipboard_box.drag_drop_cb)
        self.connect("drag_data_received",
                     self._clipboard_box.drag_data_received_cb)
        
        # Offering dnd drags
        self.drag_source_set(0, [], 0)
        self.add_events(gtk.gdk.BUTTON_PRESS_MASK |
                        gtk.gdk.POINTER_MOTION_HINT_MASK)
        self.connect("motion_notify_event",
                     self._clipboard_box.motion_notify_event_cb)

        # FIXME I'm not sure we should expose the canvas in the Window API
        self._canvas.connect("button_press_event",
                             self._clipboard_box.button_press_event_cb)

        self.connect("drag_end", self._clipboard_box.drag_end_cb)
        self.connect("drag_data_get", self._clipboard_box.drag_data_get_cb)

    def _owner_change_cb(self, clipboard, event):
        logging.debug("owner_change_cb")

        if self._clipboard_box.owns_clipboard():
            return

        cb_service = clipboardservice.get_instance()
        key = cb_service.add_object(name="")
        cb_service.set_object_percent(key, percent=0)
        
        targets = clipboard.wait_for_targets()
        for target in targets:
            if target not in ('TIMESTAMP', 'TARGETS', 'MULTIPLE', 'SAVE_TARGETS'):
                selection = clipboard.wait_for_contents(target)
                if selection:
                    self._add_selection(key, selection)

        cb_service.set_object_percent(key, percent=100)

    def _add_selection(self, key, selection):
        if selection.data:
            logging.debug('adding type ' + selection.type + '.')
                        
            cb_service = clipboardservice.get_instance()
            cb_service.add_object_format(key, 
                                  selection.type,
                                  selection.data,
                                  on_disk = False)
