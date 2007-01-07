import gtk
import gobject
import hippo

from sugar.graphics.menu import Menu
from sugar.graphics.canvasicon import CanvasIcon
from sugar.graphics.ClipboardBubble import ClipboardBubble
from sugar.graphics import style

class ClipboardMenuItem(ClipboardBubble):

    def __init__(self, percent = 0, stylesheet="clipboard.Bubble"):
        ClipboardBubble.__init__(self, percent = percent)
        style.apply_stylesheet(self, stylesheet)

class ClipboardMenu(Menu):

    ACTION_DELETE = 0
    ACTION_SHARE = 1
    ACTION_STOP_DOWNLOAD = 2
    
    def __init__(self, name, percent, preview):
        Menu.__init__(self, name)

        if percent < 100:        
            self._progress_bar = ClipboardMenuItem(percent)
            self._root.append(self._progress_bar)
        else:
            self._progress_bar = None
        
        self._remove_icon = None
        self._stop_icon = None
        
        self.add_item(preview, wrap=True)
        
        self._update_icons(percent)
        
    def _update_icons(self, percent):            
        if percent == 100:
            if not self._remove_icon:
                self._remove_icon = CanvasIcon(icon_name='stock-remove')
                self.add_action(self._remove_icon, ClipboardMenu.ACTION_DELETE)
            
            if self._stop_icon:
                self.remove_action(self._stop_icon)
                self._stop_icon = None
        else:
            if not self._stop_icon:
                self._stop_icon = CanvasIcon(icon_name='stock-close')
                self.add_action(self._stop_icon, ClipboardMenu.ACTION_STOP_DOWNLOAD)

            if self._remove_icon:
                self.remove_action(self._remove_icon)
                self._remove_icon = None
    
    def set_state(self, name, percent, preview):
        self.set_title(name)
        if self._progress_bar:
            self._progress_bar.set_property('percent', percent)
            self._update_icons(percent)
