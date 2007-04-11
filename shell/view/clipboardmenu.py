from gettext import gettext as _

import hippo

from sugar.graphics.menu import Menu, MenuItem
from sugar.graphics.canvasicon import CanvasIcon
from sugar.graphics.ClipboardBubble import ClipboardBubble
from sugar.graphics import color
from sugar.graphics import font

class ClipboardProgressBar(ClipboardBubble):

    def __init__(self, percent = 0):
        self._text_item = None
        ClipboardBubble.__init__(self, percent=percent)

        self._text_item = hippo.CanvasText(text=str(percent) + ' %')
        self._text_item.props.color = color.LABEL_TEXT.get_int()
        self._text_item.props.font_desc = font.DEFAULT.get_pango_desc()

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
    
    def __init__(self, name, percent, preview):
        Menu.__init__(self, name)
        self.props.border = 0
        
        self._activities = None

        if percent < 100:        
            self._progress_bar = ClipboardProgressBar(percent)
            self.append(self._progress_bar)
        else:
            self._progress_bar = None
        
        self._remove_item = None
        self._open_item = None
        self._stop_item = None

        if preview:
            self._preview_text = hippo.CanvasText(text=preview,
                    size_mode=hippo.CANVAS_SIZE_WRAP_WORD)
            self._preview_text.props.color = color.LABEL_TEXT.get_int()
            self._preview_text.props.font_desc = font.DEFAULT.get_pango_desc()        
            self.append(self._preview_text)
        
        self._update_icons(percent)
        
    def _update_icons(self, percent):
        if percent == 100 and self._activities:
            if not self._remove_item:
                self._remove_item = MenuItem(ClipboardMenu.ACTION_DELETE,
                                             _('Remove'),
                                             'theme:stock-remove')
                self.add_item(self._remove_item)
                            
            if not self._open_item:
                self._open_item = MenuItem(ClipboardMenu.ACTION_OPEN,
                                           _('Open'),
                                           'theme:stock-keep')
                self.add_item(self._open_item)
                            
            if self._stop_item:
                self.remove_item(self._stop_item)
                self._stop_item = None
        elif percent == 100 and not self._activities:
            if not self._remove_item:
                self._remove_item = MenuItem(ClipboardMenu.ACTION_DELETE,
                                             _('Remove'),
                                             'theme:stock-remove')
                self.add_item(self._remove_item)

            if self._open_item:
                self.remove_item(self._open_item)
                self._open_item = None

            if self._stop_item:
                self.remove_item(self._stop_item)
                self._stop_item = None        
        else:
            if not self._stop_item:
                self._stop_item = MenuItem(ClipboardMenu.ACTION_STOP_DOWNLOAD,
                                           _('Stop download'),
                                           'theme:stock-close')
                self.add_item(self._stop_item)

            if self._remove_item:
                self.remove_item(self._remove_item)
                self._remove_item = None

            if self._open_item:
                self.remove_item(self._open_item)
                self._open_item = None

    def _open_file(self):
        if self._percent < 100 or not self._activity:
            return

        # Get the file path
        cb_service = clipboardservice.get_instance()
        obj = cb_service.get_object(self._object_id)
        formats = obj['FORMATS']
        if len(formats) > 0:
            path = cb_service.get_object_data(self._object_id, formats[0])

            # FIXME: would be better to check for format.onDisk
            try:
                path_exists = os.path.exists(path)
            except TypeError:
                path_exists = False

            if path_exists:
                uri = 'file://' + path
                activityfactory.create_with_uri(self._activity, uri)
            else:
                logging.debug("Clipboard item file path %s didn't exist" % path)

    def set_activities(self, activities):
        self._activities = activities

    def set_state(self, percent):
        if self._progress_bar:
            self._progress_bar.props.percent = percent
            self._update_icons(percent)
