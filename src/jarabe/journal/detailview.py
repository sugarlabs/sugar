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

from sugar.graphics import style
from sugar.graphics.icon import CanvasIcon

from jarabe.journal.expandedentry import ExpandedEntry
from jarabe.journal import model


class DetailView(gtk.VBox):
    __gtype_name__ = 'DetailView'

    __gsignals__ = {
        'go-back-clicked': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
    }

    def __init__(self, **kwargs):
        self._metadata = None
        self._expanded_entry = None

        canvas = hippo.Canvas()

        self._root = hippo.CanvasBox()
        self._root.props.background_color = style.COLOR_PANEL_GREY.get_int()
        canvas.set_root(self._root)

        back_bar = BackBar()
        back_bar.connect('button-release-event',
                         self.__back_bar_release_event_cb)
        self._root.append(back_bar)

        gobject.GObject.__init__(self, **kwargs)

        self.pack_start(canvas)
        canvas.show()

    def _fav_icon_activated_cb(self, fav_icon):
        keep = not self._expanded_entry.get_keep()
        self._expanded_entry.set_keep(keep)
        fav_icon.props.keep = keep

    def __back_bar_release_event_cb(self, back_bar, event):
        self.emit('go-back-clicked')
        return False

    def _update_view(self):
        if self._expanded_entry is None:
            self._expanded_entry = ExpandedEntry()
            self._root.append(self._expanded_entry, hippo.PACK_EXPAND)
        self._expanded_entry.set_metadata(self._metadata)

    def refresh(self):
        logging.debug('DetailView.refresh')
        self._metadata = model.get(self._metadata['uid'])
        self._update_view()

    def get_metadata(self):
        return self._metadata

    def set_metadata(self, metadata):
        self._metadata = metadata
        self._update_view()

    metadata = gobject.property(
            type=object, getter=get_metadata, setter=set_metadata)


class BackBar(hippo.CanvasBox):
    def __init__(self):
        hippo.CanvasBox.__init__(self,
                orientation=hippo.ORIENTATION_HORIZONTAL,
                border=style.LINE_WIDTH,
                background_color=style.COLOR_PANEL_GREY.get_int(),
                border_color=style.COLOR_SELECTION_GREY.get_int(),
                padding=style.DEFAULT_PADDING,
                padding_left=style.DEFAULT_SPACING,
                spacing=style.DEFAULT_SPACING)

        icon = CanvasIcon(icon_name='go-previous',
                          size=style.SMALL_ICON_SIZE,
                          fill_color=style.COLOR_TOOLBAR_GREY.get_svg())
        self.append(icon)

        label = hippo.CanvasText(text=_('Back'),
                                 font_desc=style.FONT_NORMAL.get_pango_desc())
        self.append(label)

        if gtk.widget_get_default_direction() == gtk.TEXT_DIR_RTL:
            self.reverse()

        self.connect('motion-notify-event', self.__motion_notify_event_cb)

    def __motion_notify_event_cb(self, box, event):
        if event.detail == hippo.MOTION_DETAIL_ENTER:
            box.props.background_color = style.COLOR_SELECTION_GREY.get_int()
        elif event.detail == hippo.MOTION_DETAIL_LEAVE:
            box.props.background_color = style.COLOR_PANEL_GREY.get_int()
        return False
