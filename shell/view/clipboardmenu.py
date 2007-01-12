import logging
import gtk
import gobject
import hippo

from sugar.graphics.menu import Menu
from sugar.graphics.canvasicon import CanvasIcon
from sugar.graphics.ClipboardBubble import ClipboardBubble
from sugar.graphics import style

class ClipboardMenuItem(ClipboardBubble):

    def __init__(self, percent = 0, stylesheet="clipboard.Bubble"):
        self._text_item = None
        ClipboardBubble.__init__(self, percent=percent)
        style.apply_stylesheet(self, stylesheet)
                
        self._text_item = hippo.CanvasText(text=str(percent) + ' %')
        style.apply_stylesheet(self._text_item, 'clipboard.MenuItem.Title')
        self.append(self._text_item)
        
    def do_set_property(self, pspec, value):
        if pspec.name == 'percent':
            if self._text_item:
                self._text_item.set_property('text', str(value) + ' %')

        ClipboardBubble.do_set_property(self, pspec, value)
        
class ClipboardMenu(Menu):

    ACTION_DELETE = 0
    ACTION_OPEN = 1
    ACTION_STOP_DOWNLOAD = 2
    
    def __init__(self, name, percent, preview, activity):
        Menu.__init__(self, name)

        if percent < 100:        
            self._progress_bar = ClipboardMenuItem(percent)
            self._root.append(self._progress_bar)
        else:
            self._progress_bar = None
        
        self._remove_icon = None
        self._open_icon = None
        self._stop_icon = None
        
        self.add_item(preview, wrap=True)
        
        self._update_icons(percent, activity)
        
    def _update_icons(self, percent, activity):

        if percent == 100 and activity:
            if not self._remove_icon:
                self._remove_icon = CanvasIcon(icon_name='theme:stock-remove')
                self.add_action(self._remove_icon, ClipboardMenu.ACTION_DELETE)
                            
            if not self._open_icon:
                self._open_icon = CanvasIcon(icon_name='stock-keep')
                self.add_action(self._open_icon, ClipboardMenu.ACTION_OPEN)
                            
            if self._stop_icon:
                self.remove_action(self._stop_icon)
                self._stop_icon = None
        elif percent == 100 and not activity:
            if not self._remove_icon:
                self._remove_icon = CanvasIcon(icon_name='stock-remove')
                self.add_action(self._remove_icon, ClipboardMenu.ACTION_DELETE)

            if self._open_icon:
                self.remove_action(self._open_icon)
                self._open_icon = None

            if self._stop_icon:
                self.remove_action(self._stop_icon)
                self._stop_icon = None        
        else:
            if not self._stop_icon:
                self._stop_icon = CanvasIcon(icon_name='theme:stock-close')
                self.add_action(self._stop_icon, ClipboardMenu.ACTION_STOP_DOWNLOAD)

            if self._remove_icon:
                self.remove_action(self._remove_icon)
                self._remove_icon = None

            if self._open_icon:
                self.remove_action(self._open_icon)
                self._open_icon = None

    def set_state(self, name, percent, preview, activity):
        self.set_title(name)
        if self._progress_bar:
            self._progress_bar.set_property('percent', percent)
            self._update_icons(percent, activity)
