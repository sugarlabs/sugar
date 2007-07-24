# Copyright (C) 2007, One Laptop Per Child
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import logging
import time

import gtk
import hippo

from sugar.graphics.frame import Frame
from sugar.activity.bundle import Bundle
from sugar.date import Date
from sugar.graphics import color
from sugar.graphics import style
from sugar.graphics import units
from sugar.graphics.canvasicon import CanvasIcon
from sugar.graphics.xocolor import XoColor
from sugar.datastore import datastore
from sugar import activity
from sugar.objects import objecttype

class ObjectChooser(gtk.Dialog):
    def __init__(self, title=None, parent=None, flags=0):
        gtk.Dialog.__init__(self, title, parent, flags, (gtk.STOCK_CANCEL,
                gtk.RESPONSE_REJECT, gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        
        self._jobjects = None
        self._query = {}
        self._selected_entry = False

        self._box = hippo.CanvasBox()
        self._box.props.background_color = color.DESKTOP_BACKGROUND.get_int()
        self._box.props.spacing = units.points_to_pixels(5)
        self._box.props.padding = units.points_to_pixels(5)

        canvas = hippo.Canvas()
        canvas.set_root(self._box)

        scrolled_window = gtk.ScrolledWindow()
        scrolled_window.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)

        scrolled_window.add_with_viewport(canvas)
        canvas.show()

        self.vbox.add(scrolled_window)
        scrolled_window.show()

        scrolled_window.props.shadow_type = gtk.SHADOW_NONE
        scrolled_window.get_child().props.shadow_type = gtk.SHADOW_NONE
        
        self.refresh()
        
        height = self.get_screen().get_height() * 3 / 4
        width = self.get_screen().get_width() * 3 / 4
        self.set_default_size(width, height)

    def update_with_query(self, query):
        self._query = query
        self.refresh()

    def refresh(self):
        logging.debug('ListView.refresh: %r' % self._query)
        self._jobjects, total_count = datastore.find(self._query, sorting=['-mtime'])
        self._update()

    def _update(self):
        self._box.remove_all()
        for jobject in self._jobjects:
            entry_view = CollapsedEntry(jobject)
            entry_view.connect('button-release-event',
                                self._entry_view_button_release_event_cb)
            self._box.append(entry_view)

    def _entry_view_button_release_event_cb(self, entry_view, event):
        if self._selected_entry:
            self._selected_entry.set_selected(False)
        entry_view.set_selected(True)
        self._selected_entry = entry_view

    def get_selected_object(self):
        if self._selected_entry:
            return self._selected_entry.jobject
        else:
            return None

class CollapsedEntry(Frame):
    _DATE_COL_WIDTH    = units.points_to_pixels(75)
    _BUDDIES_COL_WIDTH = units.points_to_pixels(30)

    def __init__(self, jobject):
        Frame.__init__(self)
        self.props.box_height = units.grid_to_pixels(1)
        self.props.spacing = units.points_to_pixels(5)

        self.jobject = jobject
        self._icon_name = None

        date = hippo.CanvasText(text=self._format_date(),
                                xalign=hippo.ALIGNMENT_START,
                                font_desc=style.FONT_NORMAL.get_pango_desc(),
                                box_width=self._DATE_COL_WIDTH)
        self.append(date)

        icon = CanvasIcon(icon_name=self._get_icon_name(),
                          box_width=units.grid_to_pixels(1))

        if self.jobject.metadata.has_key('icon-color'):
            icon.props.xo_color = XoColor(self.jobject.metadata['icon-color'])

        self.append(icon)
        
        title = hippo.CanvasText(text=self._format_title(),
                                 xalign=hippo.ALIGNMENT_START,
                                 font_desc=style.FONT_BOLD.get_pango_desc(),
                                 size_mode=hippo.CANVAS_SIZE_WRAP_WORD)
        self.append(title)

    def _get_icon_name(self):
        if self._icon_name:
            return self._icon_name

        if self._is_bundle():
            bundle = Bundle(self.jobject.file_path)
            self._icon_name = bundle.get_icon()

        if self.jobject.metadata['activity']:
            service_name = self.jobject.metadata['activity']
            activity_info = activity.get_registry().get_activity(service_name)
            if activity_info:
                self._icon_name = activity_info.icon

        mime_type = self.jobject.metadata['mime_type']
        if not self._icon_name and mime_type:
            type = objecttype.get_registry().get_type_for_mime(mime_type)
            if type:
                self._icon_name = type.icon

        if not self._icon_name:
            self._icon_name = 'theme:stock-missing'

        return self._icon_name

    def _format_date(self):
        """ Convert from a string in iso format to a more human-like format. """
        ti = time.strptime(self.jobject.metadata['mtime'], "%Y-%m-%dT%H:%M:%S")        
        return str(Date(time.mktime(ti)))

    def _is_bundle(self):
        return self.jobject.metadata['mime_type'] == 'application/vnd.olpc-x-sugar'

    def _format_title(self):
        return '"%s"' % self.jobject.metadata['title']

    def set_selected(self, selected):
        if selected:
            self.props.border_color = color.WHITE.get_int()
            self.props.background_color = color.WHITE.get_int()
        else:
            self.props.border_color = color.FRAME_BORDER.get_int()
            self.props.background_color = color.DESKTOP_BACKGROUND.get_int()
