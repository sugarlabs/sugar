# Copyright (C) 2009, Aleksey Lim
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

import sys
import gobject
import hippo
import pango

from sugar.graphics import style
from sugar.graphics.icon import CanvasIcon
from sugar.graphics.xocolor import XoColor
from sugar.graphics.palette import CanvasInvoker

from jarabe.journal.keepicon import KeepIcon
from jarabe.journal.source import Source
from jarabe.journal.objectmodel import ObjectModel
from jarabe.journal.tableview import TableView, TableCell
from jarabe.journal.palettes import ObjectPalette
from jarabe.journal import misc
from jarabe.journal import model

ROWS = 4
COLUMNS = 5
STAR_WIDTH = 30


class ThumbsCell(TableCell, hippo.CanvasBox):

    def __init__(self):
        TableCell.__init__(self)

        self._last_uid = None

        hippo.CanvasBox.__init__(self,
                orientation=hippo.ORIENTATION_HORIZONTAL,
                padding_left=style.DEFAULT_SPACING,
                padding_top=style.DEFAULT_SPACING * 2,
                spacing=style.DEFAULT_PADDING)

        self.connect('button-release-event', self.__button_release_event_cb)

        # tools column

        tools_box = hippo.CanvasBox(
                spacing=style.DEFAULT_PADDING,
                orientation=hippo.ORIENTATION_VERTICAL,
                box_width=STAR_WIDTH)
        self.append(tools_box)

        self.keep = KeepIcon(False)
        self.keep.props.size = style.SMALL_ICON_SIZE
        self.keep.connect('activated', self.__star_activated_cb)
        tools_box.append(self.keep)

        details = DetailsIcon(
                size=style.SMALL_ICON_SIZE)
        details.connect('activated', self.__detail_activated_cb)
        tools_box.append(details)

        # main column

        main_box = hippo.CanvasBox(
                orientation=hippo.ORIENTATION_VERTICAL)
        self.append(main_box, hippo.PACK_EXPAND)

        self.allocation_box = hippo.CanvasBox()
        main_box.append(self.allocation_box, hippo.PACK_EXPAND)

        self.activity_box = hippo.CanvasBox(
                border=style.LINE_WIDTH,
                border_color=style.COLOR_BUTTON_GREY.get_int())
        self.allocation_box.append(self.activity_box, hippo.PACK_FIXED)

        self.thumb = ThumbCanvas(self,
                xalign=hippo.ALIGNMENT_START,
                yalign=hippo.ALIGNMENT_START)
        self.thumb.connect('detail-clicked', self.__detail_clicked_cb)
        self.activity_box.append(self.thumb, hippo.PACK_FIXED)

        self.activity_icon = ActivityIcon(self,
                xalign=hippo.ALIGNMENT_START,
                yalign=hippo.ALIGNMENT_START)
        self.activity_icon.connect('detail-clicked', self.__detail_clicked_cb)
        self.activity_box.append(self.activity_icon, hippo.PACK_EXPAND)

        self.title = hippo.CanvasText(
                padding_top=style.DEFAULT_PADDING,
                xalign=hippo.ALIGNMENT_START,
                size_mode=hippo.CANVAS_SIZE_ELLIPSIZE_END)
        main_box.append(self.title)

        self.date = hippo.CanvasText(
                xalign=hippo.ALIGNMENT_START,
                size_mode=hippo.CANVAS_SIZE_ELLIPSIZE_END)
        main_box.append(self.date)

    def do_fill_in(self):
        title_weight = pango.AttrWeight(pango.WEIGHT_BOLD)
        title_weight.start_index = 0
        title_weight.end_index = sys.maxint
        title_attributes = pango.AttrList()
        title_attributes.insert(title_weight)

        self.title.props.attributes = title_attributes
        self.title.props.text = self.row[Source.FIELD_TITLE] or ''

        self.date.props.text = self.row[Source.FIELD_MODIFY_TIME] or ''
        self.keep.props.keep = int(self.row[Source.FIELD_KEEP] or 0) == 1

        w, h = self.table.thumb_size
        self.activity_box.props.box_width = w
        self.activity_box.props.box_height = h

        thumb = self.row[Source.FIELD_THUMB]

        if self._last_uid == self.row[Source.FIELD_UID] and \
                not ObjectModel.FIELD_FETCHED_FLAG in self.row:
            # do not blink by preview while re-reading entries
            return
        else:
            self._last_uid = self.row[Source.FIELD_UID]

        if thumb is None:
            self.thumb.set_visible(False)
            self.activity_icon.set_visible(True)
            self.activity_icon.palette = None
            self.activity_icon.update_icon()
        else:
            self.activity_icon.set_visible(False)
            self.thumb.set_visible(True)
            self.thumb.props.scale_width = w - style.LINE_WIDTH * 2
            self.thumb.props.scale_height = h - style.LINE_WIDTH * 2
            self.thumb.props.image = thumb
            self.thumb.palette = None
            self.thumb.allocate(w, h, True)
            self.activity_box.set_position(self.thumb,
                    style.LINE_WIDTH, style.LINE_WIDTH)

    def __star_activated_cb(self, keep_button):
        self.row.metadata['keep'] = not keep_button.props.keep and 1 or 0
        model.write(self.row.metadata, update_mtime=False)

    def __detail_activated_cb(self, button):
        self.table.emit('detail-clicked', self.row[Source.FIELD_UID])

    def __detail_clicked_cb(self, sender, uid):
        self.table.emit('detail-clicked', uid)

    def __button_release_event_cb(self, sender, event):
        if not self.table.props.hover_selection:
            return False
        uid = self.row[Source.FIELD_UID]
        self.table.emit('entry-activated', uid)
        return False


class ActivityCanvas(object):

    def __init__(self, cell):
        self._cell = cell
        self.connect_after('button-release-event',
                self.__button_release_event_cb)
        self.palette = None

    def create_palette(self):
        if self._cell.table.props.hover_selection:
            return
        palette = ObjectPalette(self._cell.row.metadata, detail=True)
        palette.connect('detail-clicked', self.__detail_clicked_cb)
        return palette

    def __detail_clicked_cb(self, palette, uid):
        self.emit('detail-clicked', uid)

    def __button_release_event_cb(self, button, event):
        misc.resume(self._cell.row.metadata)
        return True


class ActivityIcon(ActivityCanvas, CanvasIcon):

    __gsignals__ = {
            'detail-clicked': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                              ([str])),
            }

    def __init__(self, cell, **kwargs):
        CanvasIcon.__init__(self, **kwargs)
        ActivityCanvas.__init__(self, cell)

    def update_icon(self):
        metadata = self._cell.row.metadata
        self.props.file_name = misc.get_icon_name(metadata)

        if misc.is_activity_bundle(metadata):
            self.props.fill_color = style.COLOR_TRANSPARENT.get_svg()
            self.props.stroke_color = style.COLOR_BUTTON_GREY.get_svg()
        else:
            if 'icon-color' in metadata and metadata['icon-color']:
                self.props.xo_color = XoColor(metadata['icon-color'])


class ThumbCanvas(ActivityCanvas, hippo.CanvasImage):

    __gsignals__ = {
            'detail-clicked': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                              ([str])),
            }

    def __init__(self, cell, **kwargs):
        hippo.CanvasImage.__init__(self, **kwargs)
        ActivityCanvas.__init__(self, cell)

        self._palette_invoker = CanvasInvoker()
        self._palette_invoker.attach(self)
        self.connect('destroy', self.__destroy_cb)

    def __destroy_cb(self, icon):
        if self._palette_invoker is not None:
            self._palette_invoker.detach()


class DetailsIcon(CanvasIcon):

    def __init__(self, **kwargs):
        CanvasIcon.__init__(self, **kwargs)
        self.props.icon_name = 'go-right'
        self.props.stroke_color = style.COLOR_TRANSPARENT.get_svg()
        self.connect('motion-notify-event', self.__motion_notify_event_cb)
        self.connect('activated', self.__on_leave_cb)
        self.__on_leave_cb(None)

    def __on_leave_cb(self, button):
        self.props.fill_color = style.COLOR_BUTTON_GREY.get_svg()

    def __motion_notify_event_cb(self, icon, event):
        if event.detail == hippo.MOTION_DETAIL_ENTER:
            icon.props.fill_color = style.COLOR_BLACK.get_svg()
        elif event.detail == hippo.MOTION_DETAIL_LEAVE:
            self.__on_leave_cb(None)


class ThumbsView(TableView):

    __gsignals__ = {
            'detail-clicked': (gobject.SIGNAL_RUN_FIRST,
                              gobject.TYPE_NONE,
                              ([object])),
            'entry-activated': (gobject.SIGNAL_RUN_FIRST,
                                gobject.TYPE_NONE,
                                ([str])),
            }

    def __init__(self):
        TableView.__init__(self, ThumbsCell, ROWS, COLUMNS)
        self.thumb_size = (0, 0)

    def do_size_allocate(self, allocation):
        text_layout = self.create_pango_layout('W')
        w = allocation.width / COLUMNS - STAR_WIDTH - style.DEFAULT_SPACING - \
                style.DEFAULT_PADDING - style.LINE_WIDTH * 2
        h = allocation.height / ROWS - text_layout.get_pixel_size()[1] * 2 - \
                style.DEFAULT_SPACING * 2 - style.DEFAULT_PADDING - \
                style.LINE_WIDTH * 2

        # keep thumb size 4:3
        if w / 4. * 3. > h:
            w = int(h / 3. * 4.)
        else:
            h = int(w / 4. * 3.)

        self.thumb_size = (max(0, w), max(0, h))

        TableView.do_size_allocate(self, allocation)
