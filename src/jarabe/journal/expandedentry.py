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
import StringIO
import time
import os

import hippo
import cairo
import gobject
import glib
import gtk
import simplejson

from sugar.graphics import style
from sugar.graphics.icon import CanvasIcon
from sugar.graphics.xocolor import XoColor
from sugar.graphics.canvastextview import CanvasTextView
from sugar.util import format_size

from jarabe.journal.keepicon import KeepIcon
from jarabe.journal.palettes import ObjectPalette, BuddyPalette
from jarabe.journal import misc
from jarabe.journal import model


class Separator(hippo.CanvasBox, hippo.CanvasItem):
    def __init__(self, orientation):
        hippo.CanvasBox.__init__(self,
                background_color=style.COLOR_PANEL_GREY.get_int())

        if orientation == hippo.ORIENTATION_VERTICAL:
            self.props.box_width = style.LINE_WIDTH
        else:
            self.props.box_height = style.LINE_WIDTH


class BuddyList(hippo.CanvasBox):
    def __init__(self, buddies):
        hippo.CanvasBox.__init__(self, xalign=hippo.ALIGNMENT_START,
                                 orientation=hippo.ORIENTATION_HORIZONTAL)

        for buddy in buddies:
            nick_, color = buddy
            hbox = hippo.CanvasBox(orientation=hippo.ORIENTATION_HORIZONTAL)
            icon = CanvasIcon(icon_name='computer-xo',
                              xo_color=XoColor(color),
                              size=style.STANDARD_ICON_SIZE)
            icon.set_palette(BuddyPalette(buddy))
            hbox.append(icon)
            self.append(hbox)


class ExpandedEntry(hippo.CanvasBox):
    def __init__(self):
        hippo.CanvasBox.__init__(self)
        self.props.orientation = hippo.ORIENTATION_VERTICAL
        self.props.background_color = style.COLOR_WHITE.get_int()
        self.props.padding_top = style.DEFAULT_SPACING * 3

        self._metadata = None
        self._update_title_sid = None

        # Create header
        header = hippo.CanvasBox(orientation=hippo.ORIENTATION_HORIZONTAL,
                                 padding=style.DEFAULT_PADDING,
                                 padding_right=style.GRID_CELL_SIZE,
                                 spacing=style.DEFAULT_SPACING)
        self.append(header)

        # Create two column body

        body = hippo.CanvasBox(orientation=hippo.ORIENTATION_HORIZONTAL,
                               spacing=style.DEFAULT_SPACING * 3,
                               padding_left=style.GRID_CELL_SIZE,
                               padding_right=style.GRID_CELL_SIZE,
                               padding_top=style.DEFAULT_SPACING * 3)

        self.append(body, hippo.PACK_EXPAND)

        first_column = hippo.CanvasBox(orientation=hippo.ORIENTATION_VERTICAL,
                                       spacing=style.DEFAULT_SPACING)
        body.append(first_column)

        second_column = hippo.CanvasBox(orientation=hippo.ORIENTATION_VERTICAL,
                                       spacing=style.DEFAULT_SPACING)
        body.append(second_column, hippo.PACK_EXPAND)

        # Header

        self._keep_icon = self._create_keep_icon()
        header.append(self._keep_icon)

        self._icon = None
        self._icon_box = hippo.CanvasBox()
        header.append(self._icon_box)

        self._title = self._create_title()
        header.append(self._title, hippo.PACK_EXPAND)

        # TODO: create a version list popup instead of a date label
        self._date = self._create_date()
        header.append(self._date)

        if gtk.widget_get_default_direction() == gtk.TEXT_DIR_RTL:
            header.reverse()

        # First column

        self._preview_box = hippo.CanvasBox()
        first_column.append(self._preview_box)

        self._technical_box = hippo.CanvasBox()
        first_column.append(self._technical_box)

        # Second column

        description_box, self._description = self._create_description()
        second_column.append(description_box)

        tags_box, self._tags = self._create_tags()
        second_column.append(tags_box)

        self._buddy_list = hippo.CanvasBox()
        second_column.append(self._buddy_list)

    def set_metadata(self, metadata):
        if self._metadata == metadata:
            return
        self._metadata = metadata

        self._keep_icon.keep = (str(metadata.get('keep', 0)) == '1')

        self._icon = self._create_icon()
        self._icon_box.clear()
        self._icon_box.append(self._icon)

        self._date.props.text = misc.get_date(metadata)

        title = self._title.props.widget
        title.props.text = metadata.get('title', _('Untitled'))
        title.props.editable = model.is_editable(metadata)

        self._preview_box.clear()
        self._preview_box.append(self._create_preview())

        self._technical_box.clear()
        self._technical_box.append(self._create_technical())

        self._buddy_list.clear()
        self._buddy_list.append(self._create_buddy_list())

        description = self._description.text_view_widget
        description.props.buffer.props.text = metadata.get('description', '')
        description.props.editable = model.is_editable(metadata)

        tags = self._tags.text_view_widget
        tags.props.buffer.props.text = metadata.get('tags', '')
        tags.props.editable = model.is_editable(metadata)

    def _create_keep_icon(self):
        keep_icon = KeepIcon(False)
        keep_icon.connect('activated', self._keep_icon_activated_cb)
        return keep_icon

    def _create_icon(self):
        icon = CanvasIcon(file_name=misc.get_icon_name(self._metadata))
        icon.connect_after('button-release-event',
                           self._icon_button_release_event_cb)

        if misc.is_activity_bundle(self._metadata):
            xo_color = XoColor('%s,%s' % (style.COLOR_BUTTON_GREY.get_svg(),
                                          style.COLOR_TRANSPARENT.get_svg()))
        else:
            xo_color = misc.get_icon_color(self._metadata)
        icon.props.xo_color = xo_color

        icon.set_palette(ObjectPalette(self._metadata))

        return icon

    def _create_title(self):
        entry = gtk.Entry()
        entry.connect('focus-out-event', self._title_focus_out_event_cb)

        bg_color = style.COLOR_WHITE.get_gdk_color()
        entry.modify_bg(gtk.STATE_INSENSITIVE, bg_color)
        entry.modify_base(gtk.STATE_INSENSITIVE, bg_color)

        return hippo.CanvasWidget(widget=entry)

    def _create_date(self):
        date = hippo.CanvasText(xalign=hippo.ALIGNMENT_START,
                                font_desc=style.FONT_NORMAL.get_pango_desc())
        return date

    def _create_preview(self):
        width = style.zoom(320)
        height = style.zoom(240)
        box = hippo.CanvasBox()

        if len(self._metadata.get('preview', '')) > 4:
            if self._metadata['preview'][1:4] == 'PNG':
                preview_data = self._metadata['preview']
            else:
                # TODO: We are close to be able to drop this.
                import base64
                preview_data = base64.b64decode(
                        self._metadata['preview'])

            png_file = StringIO.StringIO(preview_data)
            try:
                surface = cairo.ImageSurface.create_from_png(png_file)
                has_preview = True
            except Exception:
                logging.exception('Error while loading the preview')
                has_preview = False
        else:
            has_preview = False

        if has_preview:
            preview_box = hippo.CanvasImage(image=surface,
                    border=style.LINE_WIDTH,
                    border_color=style.COLOR_BUTTON_GREY.get_int(),
                    xalign=hippo.ALIGNMENT_CENTER,
                    yalign=hippo.ALIGNMENT_CENTER,
                    scale_width=width,
                    scale_height=height)
        else:
            preview_box = hippo.CanvasText(text=_('No preview'),
                    font_desc=style.FONT_NORMAL.get_pango_desc(),
                    xalign=hippo.ALIGNMENT_CENTER,
                    yalign=hippo.ALIGNMENT_CENTER,
                    border=style.LINE_WIDTH,
                    border_color=style.COLOR_BUTTON_GREY.get_int(),
                    color=style.COLOR_BUTTON_GREY.get_int(),
                    box_width=width,
                    box_height=height)
        preview_box.connect_after('button-release-event',
                                  self._preview_box_button_release_event_cb)
        box.append(preview_box)
        return box

    def _create_technical(self):
        vbox = hippo.CanvasBox()
        vbox.props.spacing = style.DEFAULT_SPACING

        lines = [
            _('Kind: %s') % (self._metadata.get('mime_type') or _('Unknown'),),
            _('Date: %s') % (self._format_date(),),
            _('Size: %s') % (format_size(int(self._metadata.get('filesize',
                                model.get_file_size(self._metadata['uid']))))),
            ]

        for line in lines:
            text = hippo.CanvasText(text=line,
                font_desc=style.FONT_NORMAL.get_pango_desc())
            text.props.color = style.COLOR_BUTTON_GREY.get_int()

            if gtk.widget_get_default_direction() == gtk.TEXT_DIR_RTL:
                text.props.xalign = hippo.ALIGNMENT_END
            else:
                text.props.xalign = hippo.ALIGNMENT_START

            vbox.append(text)

        return vbox

    def _format_date(self):
        if 'timestamp' in self._metadata:
            try:
                timestamp = float(self._metadata['timestamp'])
            except (ValueError, TypeError):
                logging.warning('Invalid timestamp for %r: %r',
                                self._metadata['uid'],
                                self._metadata['timestamp'])
            else:
                return time.strftime('%x', time.localtime(timestamp))
        return _('No date')

    def _create_buddy_list(self):

        vbox = hippo.CanvasBox()
        vbox.props.spacing = style.DEFAULT_SPACING

        text = hippo.CanvasText(text=_('Participants:'),
                                font_desc=style.FONT_NORMAL.get_pango_desc())
        text.props.color = style.COLOR_BUTTON_GREY.get_int()

        if gtk.widget_get_default_direction() == gtk.TEXT_DIR_RTL:
            text.props.xalign = hippo.ALIGNMENT_END
        else:
            text.props.xalign = hippo.ALIGNMENT_START

        vbox.append(text)

        if self._metadata.get('buddies'):
            buddies = simplejson.loads(self._metadata['buddies']).values()
            vbox.append(BuddyList(buddies))
            return vbox
        else:
            return vbox

    def _create_description(self):
        vbox = hippo.CanvasBox()
        vbox.props.spacing = style.DEFAULT_SPACING

        text = hippo.CanvasText(text=_('Description:'),
                                font_desc=style.FONT_NORMAL.get_pango_desc())
        text.props.color = style.COLOR_BUTTON_GREY.get_int()

        if gtk.widget_get_default_direction() == gtk.TEXT_DIR_RTL:
            text.props.xalign = hippo.ALIGNMENT_END
        else:
            text.props.xalign = hippo.ALIGNMENT_START

        vbox.append(text)

        text_view = CanvasTextView('',
                box_height=style.GRID_CELL_SIZE * 2)
        vbox.append(text_view, hippo.PACK_EXPAND)

        text_view.text_view_widget.props.accepts_tab = False
        text_view.text_view_widget.connect('focus-out-event',
                self._description_focus_out_event_cb)

        return vbox, text_view

    def _create_tags(self):
        vbox = hippo.CanvasBox()
        vbox.props.spacing = style.DEFAULT_SPACING

        text = hippo.CanvasText(text=_('Tags:'),
                                font_desc=style.FONT_NORMAL.get_pango_desc())
        text.props.color = style.COLOR_BUTTON_GREY.get_int()

        if gtk.widget_get_default_direction() == gtk.TEXT_DIR_RTL:
            text.props.xalign = hippo.ALIGNMENT_END
        else:
            text.props.xalign = hippo.ALIGNMENT_START

        vbox.append(text)

        text_view = CanvasTextView('',
                box_height=style.GRID_CELL_SIZE * 2)
        vbox.append(text_view, hippo.PACK_EXPAND)

        text_view.text_view_widget.props.accepts_tab = False
        text_view.text_view_widget.connect('focus-out-event',
                self._tags_focus_out_event_cb)

        return vbox, text_view

    def _title_notify_text_cb(self, entry, pspec):
        if not self._update_title_sid:
            self._update_title_sid = gobject.timeout_add_seconds(1,
                                                         self._update_title_cb)

    def _title_focus_out_event_cb(self, entry, event):
        self._update_entry()

    def _description_focus_out_event_cb(self, text_view, event):
        self._update_entry()

    def _tags_focus_out_event_cb(self, text_view, event):
        self._update_entry()

    def _update_entry(self, needs_update=False):
        if not model.is_editable(self._metadata):
            return

        old_title = self._metadata.get('title', None)
        new_title = self._title.props.widget.props.text
        if old_title != new_title:
            label = glib.markup_escape_text(new_title)
            self._icon.palette.props.primary_text = label
            self._metadata['title'] = new_title
            self._metadata['title_set_by_user'] = '1'
            needs_update = True

        old_tags = self._metadata.get('tags', None)
        new_tags = self._tags.text_view_widget.props.buffer.props.text
        if old_tags != new_tags:
            self._metadata['tags'] = new_tags
            needs_update = True

        old_description = self._metadata.get('description', None)
        new_description = \
                self._description.text_view_widget.props.buffer.props.text
        if old_description != new_description:
            self._metadata['description'] = new_description
            needs_update = True

        if needs_update:
            if self._metadata.get('mountpoint', '/') == '/':
                model.write(self._metadata, update_mtime=False)
            else:
                old_file_path = os.path.join(self._metadata['mountpoint'],
                        model.get_file_name(old_title,
                        self._metadata['mime_type']))
                model.write(self._metadata, file_path=old_file_path,
                        update_mtime=False)

        self._update_title_sid = None

    def get_keep(self):
        return (str(self._metadata.get('keep', 0)) == '1')

    def _keep_icon_activated_cb(self, keep_icon):
        if self.get_keep():
            self._metadata['keep'] = 0
        else:
            self._metadata['keep'] = 1
        self._update_entry(needs_update=True)
        keep_icon.props.keep = self.get_keep()

    def _icon_button_release_event_cb(self, button, event):
        logging.debug('_icon_button_release_event_cb')
        misc.resume(self._metadata)
        return True

    def _preview_box_button_release_event_cb(self, button, event):
        logging.debug('_preview_box_button_release_event_cb')
        misc.resume(self._metadata)
        return True
