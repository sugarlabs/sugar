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
from gettext import gettext as _

import gtk
import hippo

from sugar.bundle.activitybundle import ActivityBundle
from sugar.graphics import style
from sugar.graphics.icon import CanvasIcon
from sugar.graphics.xocolor import XoColor
from sugar.graphics.roundbox import CanvasRoundBox
from sugar.datastore import datastore
from sugar import activity

# TODO: Activities should request the Journal to open objectchooser dialogs. In
# that way, we'll be able to reuse most of this code inside the Journal.

class ObjectChooser(gtk.Dialog):
    def __init__(self, title=None, parent=None, flags=0):
        gtk.Dialog.__init__(self, title, parent, flags, (gtk.STOCK_CANCEL,
                gtk.RESPONSE_REJECT, gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        
        self._jobjects = None
        self._query = {}
        self._selected_entry = False

        self._box = hippo.CanvasBox()
        self._box.props.background_color = style.COLOR_PANEL_GREY.get_int()
        self._box.props.spacing = style.DEFAULT_SPACING
        self._box.props.padding = style.DEFAULT_SPACING

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

class CollapsedEntry(CanvasRoundBox):
    _DATE_COL_WIDTH    = style.zoom(100)
    _BUDDIES_COL_WIDTH = style.zoom(50)

    def __init__(self, jobject):
        CanvasRoundBox.__init__(self)
        self.props.box_height = style.zoom(75)
        self.props.spacing = style.DEFAULT_SPACING
        self.props.border_color = style.COLOR_BLACK.get_int()
        self.props.background_color = style.COLOR_PANEL_GREY.get_int()

        self.jobject = jobject
        self._icon_name = None

        date = hippo.CanvasText(text=self._format_date(),
                                xalign=hippo.ALIGNMENT_START,
                                font_desc=style.FONT_NORMAL.get_pango_desc(),
                                box_width=self._DATE_COL_WIDTH)
        self.append(date)

        icon = CanvasIcon(icon_name=self._get_icon_name(),
                          box_width=style.zoom(75))

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

        if self.jobject.is_activity_bundle():
            bundle = ActivityBundle(self.jobject.file_path)
            self._icon_name = bundle.get_icon()

        if self.jobject.metadata['activity']:
            service_name = self.jobject.metadata['activity']
            activity_info = activity.get_registry().get_activity(service_name)
            if activity_info:
                self._icon_name = activity_info.icon

        mime_type = self.jobject.metadata['mime_type']
        if not self._icon_name and mime_type:
            self._icon_name = mime.get_mime_icon(mime_type)
        if not self._icon_name:
            self._icon_name = 'image-missing'

        return self._icon_name

    def _format_date(self):
        """ Convert from a string in iso format to a more human-like format. """
        return _get_elapsed_string(self.jobject.metadata['mtime'])

    def _format_title(self):
        return '"%s"' % self.jobject.metadata['title']

    def set_selected(self, selected):
        if selected:
            self.props.border_color = style.COLOR_WHITE.get_int()
            self.props.background_color = style.COLOR_WHITE.get_int()
        else:
            self.props.border_color = style.COLOR_BLACK.get_int()
            self.props.background_color = style.COLOR_PANEL_GREY.get_int()

def _get_elapsed_string(date_string, max_levels=2):
    ti = time.strptime(date_string, "%Y-%m-%dT%H:%M:%S")

    units = [[_('%d year'),   _('%d years'),   356 * 24 * 60 * 60],
             [_('%d month'),  _('%d months'),  30 * 24 * 60 * 60],
             [_('%d week'),   _('%d weeks'),   7 * 24 * 60 * 60],
             [_('%d day'),    _('%d days'),    24 * 60 * 60],
             [_('%d hour'),   _('%d hours'),   60 * 60],
             [_('%d minute'), _('%d minutes'), 60],
             [_('%d second'), _('%d seconds'), 1]]
    levels = 0
    result = ''
    elapsed_seconds = int(time.time() - time.mktime(ti))
    for name_singular, name_plural, factor in units:
        elapsed_units = elapsed_seconds / factor
        if elapsed_units > 0:

            if levels > 0:
                if max_levels - levels == 1:
                    result += _(' and ')
                else:
                    result += _(', ')
                
            if elapsed_units == 1:
                result += name_singular % elapsed_units
            else:
                result += name_plural % elapsed_units
            elapsed_seconds -= elapsed_units * factor
            levels += 1
            
            if levels == max_levels:
                break

    return result

