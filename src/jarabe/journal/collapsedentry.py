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

import logging
from gettext import gettext as _

import gobject
import gtk
import hippo
import cjson

from sugar.graphics.icon import CanvasIcon
from sugar.graphics.xocolor import XoColor
from sugar.graphics import style
from sugar.graphics.entry import CanvasEntry

from jarabe.journal.keepicon import KeepIcon
from jarabe.journal.palettes import ObjectPalette, BuddyPalette
from jarabe.journal import misc
from jarabe.journal import model

class BuddyIcon(CanvasIcon):
    def __init__(self, buddy, **kwargs):
        CanvasIcon.__init__(self, **kwargs)
        self._buddy = buddy

    def create_palette(self):
        return BuddyPalette(self._buddy)

class BuddyList(hippo.CanvasBox):
    def __init__(self, buddies, width):
        hippo.CanvasBox.__init__(self,
                orientation=hippo.ORIENTATION_HORIZONTAL,
                box_width=width,
                xalign=hippo.ALIGNMENT_START)
        self.set_buddies(buddies)

    def set_buddies(self, buddies):
        for item in self.get_children():
            self.remove(item)

        for buddy in buddies[0:3]:
            nick_, color = buddy
            icon = BuddyIcon(buddy,
                             icon_name='computer-xo',
                             xo_color=XoColor(color),
                             cache=True)
            self.append(icon)

class EntryIcon(CanvasIcon):
    def __init__(self, **kwargs):
        CanvasIcon.__init__(self, **kwargs)
        self._metadata = None

    def set_metadata(self, metadata):
        self._metadata = metadata
        self.props.file_name = misc.get_icon_name(metadata)
        self.palette = None

    def create_palette(self):
        if self.show_palette:
            return ObjectPalette(self._metadata)
        else:
            return None

    show_palette = gobject.property(type=bool, default=False)

class BaseCollapsedEntry(hippo.CanvasBox):
    __gtype_name__ = 'BaseCollapsedEntry'

    _DATE_COL_WIDTH     = style.GRID_CELL_SIZE * 3
    _BUDDIES_COL_WIDTH  = style.GRID_CELL_SIZE * 3
    _PROGRESS_COL_WIDTH = style.GRID_CELL_SIZE * 5

    def __init__(self):
        hippo.CanvasBox.__init__(self,
                                 spacing=style.DEFAULT_SPACING,
                                 padding_top=style.DEFAULT_PADDING,
                                 padding_bottom=style.DEFAULT_PADDING,
                                 padding_left=style.DEFAULT_PADDING * 2,
                                 padding_right=style.DEFAULT_PADDING * 2,
                                 box_height=style.GRID_CELL_SIZE,
                                 orientation=hippo.ORIENTATION_HORIZONTAL)
        
        self._metadata = None
        self._is_selected = False

        self.keep_icon = self._create_keep_icon()
        self.append(self.keep_icon)

        self.icon = self._create_icon()
        self.append(self.icon)

        self.title = self._create_title()
        self.append(self.title, hippo.PACK_EXPAND)

        self.buddies_list = self._create_buddies_list()
        self.append(self.buddies_list)

        self.date = self._create_date()
        self.append(self.date)

        # Progress controls
        self.progress_bar = self._create_progress_bar()
        self.append(self.progress_bar)

        self.cancel_button = self._create_cancel_button()
        self.append(self.cancel_button)

    def _create_keep_icon(self):
        keep_icon = KeepIcon(False)
        keep_icon.connect('button-release-event',
                          self.__keep_icon_button_release_event_cb)
        return keep_icon
    
    def _create_date(self):
        date = hippo.CanvasText(text='',
                                xalign=hippo.ALIGNMENT_START,
                                font_desc=style.FONT_NORMAL.get_pango_desc(),
                                box_width=self._DATE_COL_WIDTH)
        return date
    
    def _create_icon(self):
        icon = EntryIcon(size=style.STANDARD_ICON_SIZE, cache=True)
        return icon

    def _create_title(self):
        # TODO: We'd prefer to ellipsize in the middle
        title = hippo.CanvasText(text='',
                                 xalign=hippo.ALIGNMENT_START,
                                 font_desc=style.FONT_BOLD.get_pango_desc(),
                                 size_mode=hippo.CANVAS_SIZE_ELLIPSIZE_END)
        return title

    def _create_buddies_list(self):
        return BuddyList([], self._BUDDIES_COL_WIDTH)

    def _create_progress_bar(self):
        progress_bar = gtk.ProgressBar()
        return hippo.CanvasWidget(widget=progress_bar,
                                  yalign=hippo.ALIGNMENT_CENTER,
                                  box_width=self._PROGRESS_COL_WIDTH)

    def _create_cancel_button(self):
        button = CanvasIcon(icon_name='activity-stop',
                            size=style.SMALL_ICON_SIZE,
                            box_width=style.GRID_CELL_SIZE)
        button.connect('button-release-event',
                       self._cancel_button_release_event_cb)
        return button

    def _decode_buddies(self):
        if self.metadata.has_key('buddies') and \
           self.metadata['buddies']:
            buddies = cjson.decode(self.metadata['buddies']).values()
        else:
            buddies = []
        return buddies

    def update_visibility(self):
        in_process = self.is_in_progress()

        self.buddies_list.set_visible(not in_process)
        self.date.set_visible(not in_process)

        self.progress_bar.set_visible(in_process)
        self.cancel_button.set_visible(in_process)

    # TODO: determine the appearance of in-progress entries
    def _update_color(self):
        if self.is_in_progress():
            self.props.background_color = style.COLOR_WHITE.get_int()
        else:
            self.props.background_color = style.COLOR_WHITE.get_int()

    def is_in_progress(self):
        return self.metadata.has_key('progress') and \
                int(self.metadata['progress']) < 100

    def get_keep(self):
        keep = int(self.metadata.get('keep', 0))
        return keep == 1

    def __keep_icon_button_release_event_cb(self, button, event):
        logging.debug('__keep_icon_button_release_event_cb')
        metadata = model.get(self._metadata['uid'])
        if self.get_keep():
            metadata['keep'] = 0
        else:
            metadata['keep'] = 1
        model.write(metadata, update_mtime=False)

        self.keep_icon.props.keep = self.get_keep()
        self._update_color()

        return True

    def _cancel_button_release_event_cb(self, button, event):
        logging.debug('_cancel_button_release_event_cb')
        model.delete(self._metadata['uid'])
        return True

    def set_selected(self, is_selected):
        self._is_selected = is_selected
        self._update_color()

    def set_metadata(self, metadata):
        self._metadata = metadata
        self._is_selected = False

        self.keep_icon.props.keep = self.get_keep()

        self.date.props.text = misc.get_date(metadata)

        self.icon.set_metadata(metadata)
        if misc.is_activity_bundle(metadata):
            self.icon.props.fill_color = style.COLOR_TRANSPARENT.get_svg()
            self.icon.props.stroke_color = style.COLOR_BUTTON_GREY.get_svg()
        else:    
            if metadata.has_key('icon-color') and \
                   metadata['icon-color']:
                self.icon.props.xo_color = XoColor( \
                    metadata['icon-color'])
            else:
                self.icon.props.xo_color = None

        if metadata.get('title', ''):
            title_text = metadata['title']
        else:
            title_text = _('Untitled')
        self.title.props.text = title_text

        self.buddies_list.set_buddies(self._decode_buddies())

        if metadata.has_key('progress'):
            self.progress_bar.props.widget.props.fraction = \
                int(metadata['progress']) / 100.0

        self.update_visibility()
        self._update_color()

    def get_metadata(self):
        return self._metadata

    metadata = property(get_metadata, set_metadata)

    def update_date(self):
        self.date.props.text = misc.get_date(self._metadata)

class CollapsedEntry(BaseCollapsedEntry):
    __gtype_name__ = 'CollapsedEntry'

    __gsignals__ = {
        'detail-clicked': (gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE,
                           ([]))
    }

    def __init__(self):
        BaseCollapsedEntry.__init__(self)

        self.icon.props.show_palette = True
        self.icon.connect('button-release-event',
                          self.__icon_button_release_event_cb)

        self.title.connect('button_release_event',
                           self.__title_button_release_event_cb)

        self._title_entry = self._create_title_entry()
        self.insert_after(self._title_entry, self.title, hippo.PACK_EXPAND)
        self._title_entry.set_visible(False)

        self._detail_button = self._create_detail_button()
        self._detail_button.connect('motion-notify-event',
                                    self.__detail_button_motion_notify_event_cb)
        self.append(self._detail_button)

        if gtk.widget_get_default_direction() == gtk.TEXT_DIR_RTL:
            self.reverse()

    def _create_title_entry(self):
        title_entry = CanvasEntry()
        title_entry.set_background(style.COLOR_WHITE.get_html())
        title_entry.props.widget.connect('focus-out-event',
                self.__title_entry_focus_out_event_cb)
        title_entry.props.widget.connect('activate',
                                         self.__title_entry_activate_cb)
        title_entry.connect('key-press-event',
                            self.__title_entry_key_press_event_cb)
        return title_entry

    def _create_detail_button(self):
        button = CanvasIcon(icon_name='go-right',
                            size=style.SMALL_ICON_SIZE,
                            box_width=style.GRID_CELL_SIZE * 3 / 5,
                            fill_color=style.COLOR_BUTTON_GREY.get_svg())
        button.connect('button-release-event',
                       self.__detail_button_release_event_cb)
        return button

    def update_visibility(self):
        BaseCollapsedEntry.update_visibility(self)
        self._detail_button.set_visible(not self.is_in_progress())

    def set_metadata(self, metadata):
        BaseCollapsedEntry.set_metadata(self, metadata)
        self._title_entry.props.text = self.title.props.text

    metadata = property(BaseCollapsedEntry.get_metadata, set_metadata)

    def __detail_button_release_event_cb(self, button, event):
        logging.debug('_detail_button_release_event_cb')
        if not self.is_in_progress():
            self.emit('detail-clicked')
        return True

    def __detail_button_motion_notify_event_cb(self, button, event):
        if event.detail == hippo.MOTION_DETAIL_ENTER:
            button.props.fill_color = style.COLOR_TOOLBAR_GREY.get_svg()
        elif event.detail == hippo.MOTION_DETAIL_LEAVE:
            button.props.fill_color = style.COLOR_BUTTON_GREY.get_svg()

    def __icon_button_release_event_cb(self, button, event):
        logging.debug('__icon_button_release_event_cb')
        misc.resume(self.metadata)
        return True

    def __title_button_release_event_cb(self, button, event):
        self.title.set_visible(False)
        self._title_entry.set_visible(True)
        self._title_entry.props.widget.grab_focus()

    def __title_entry_focus_out_event_cb(self, entry, event):
        self._apply_title_change(entry.props.text)

    def __title_entry_activate_cb(self, entry):
        self._apply_title_change(entry.props.text)

    def __title_entry_key_press_event_cb(self, entry, event):
        if event.key == hippo.KEY_ESCAPE:
            self._cancel_title_change()

    def _apply_title_change(self, title):
        self._title_entry.set_visible(False)
        self.title.set_visible(True)

        if title == '':
            self._cancel_title_change()
        elif self.title.props.text != title:
            self.title.props.text = title
            self._metadata['title'] = title
            self._metadata['title_set_by_user'] = '1'
            model.write(self._metadata, update_mtime=False)

    def _cancel_title_change(self):
        self._title_entry.props.text = self.title.props.text
        self._title_entry.set_visible(False)
        self.title.set_visible(True)        

