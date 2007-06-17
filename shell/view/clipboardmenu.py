# Copyright (C) 2007, One Laptop Per Child
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
from gettext import gettext as _

import hippo

from sugar.graphics.menu import Menu, MenuItem
from sugar.graphics.canvasicon import CanvasIcon
from sugar.graphics import color
from sugar.graphics import font

from view.ClipboardBubble import ClipboardBubble

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
    ACTION_SAVE_TO_JOURNAL = 3
    
    def __init__(self, name, percent, preview, activity, installable):
        Menu.__init__(self, name)
        self.props.border = 0

        if percent < 100:        
            self._progress_bar = ClipboardProgressBar(percent)
            self.append(self._progress_bar)
        else:
            self._progress_bar = None
        
        self._remove_item = None
        self._open_item = None
        self._stop_item = None
        self._journal_item = None

        if preview:
            self._preview_text = hippo.CanvasText(text=preview,
                    size_mode=hippo.CANVAS_SIZE_WRAP_WORD)
            self._preview_text.props.color = color.LABEL_TEXT.get_int()
            self._preview_text.props.font_desc = font.DEFAULT.get_pango_desc()        
            self.append(self._preview_text)

        self._update_icons(percent, activity, installable)

    def _update_icons(self, percent, activity, installable):
        if percent == 100 and (activity or installable):
            self._add_remove_item()
            self._add_open_item()
            self._remove_stop_item()
            self._add_journal_item()
        elif percent == 100 and (not activity and not installable):
            self._add_remove_item()
            self._remove_open_item()
            self._remove_stop_item()
            self._add_journal_item()
        else:
            self._remove_remove_item()
            self._remove_open_item()
            self._add_stop_item()
            self._remove_journal_item()

    def set_state(self, name, percent, preview, activity, installable):
        self.set_title(name)
        if self._progress_bar:
            self._progress_bar.set_property('percent', percent)
            self._update_icons(percent, activity, installable)

    def _add_remove_item(self):
        if not self._remove_item:
            self._remove_item = MenuItem(ClipboardMenu.ACTION_DELETE,
                                            _('Remove'),
                                            'theme:stock-remove')
            self.add_item(self._remove_item)

    def _add_open_item(self):
        if not self._open_item:
            self._open_item = MenuItem(ClipboardMenu.ACTION_OPEN,
                                        _('Open'),
                                        'theme:stock-keep')
            self.add_item(self._open_item)

    def _add_stop_item(self):
        if not self._stop_item:
            self._stop_item = MenuItem(ClipboardMenu.ACTION_STOP_DOWNLOAD,
                                        _('Stop download'),
                                        'theme:stock-close')
            self.add_item(self._stop_item)

    def _add_journal_item(self):
        if not self._journal_item:
            self._journal_item = MenuItem(ClipboardMenu.ACTION_SAVE_TO_JOURNAL,
                                        _('Add to journal'),
                                        'theme:stock-save')
            self.add_item(self._journal_item)

    def _remove_open_item(self):
        if self._open_item:
            self.remove_item(self._open_item)
            self._open_item = None

    def _remove_stop_item(self):
        if self._stop_item:
            self.remove_item(self._stop_item)
            self._stop_item = None

    def _remove_remove_item(self):
        if self._remove_item:
            self.remove_item(self._remove_item)
            self._remove_item = None

    def _remove_journal_item(self):
        if self._journal_item:
            self.remove_item(self._journal_item)
            self._journal_item = None

