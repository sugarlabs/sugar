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

from sugar.graphics import style
from sugar.graphics.icon import Icon

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

        gobject.GObject.__init__(self, **kwargs)
        gtk.VBox.__init__(self)

        back_bar = BackBar()
        back_bar.connect('button-release-event',
                         self.__back_bar_release_event_cb)
        self.pack_start(back_bar, expand=False)

        self.show_all()

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
            self.pack_start(self._expanded_entry)
        self._expanded_entry.set_metadata(self._metadata)
        self.show_all()

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


class BackBar(gtk.EventBox):
    def __init__(self):
        gtk.EventBox.__init__(self)
        self.modify_bg(gtk.STATE_NORMAL,
                       style.COLOR_PANEL_GREY.get_gdk_color())
        hbox = gtk.HBox(spacing=style.DEFAULT_PADDING)
        hbox.set_border_width(style.DEFAULT_PADDING)
        icon = Icon(icon_name='go-previous', icon_size=gtk.ICON_SIZE_MENU,
                    fill_color=style.COLOR_TOOLBAR_GREY.get_svg())
        hbox.pack_start(icon, False, False)

        label = gtk.Label()
        label.set_text(_('Back'))
        halign = gtk.Alignment(0, 0.5, 0, 1)
        halign.add(label)
        hbox.pack_start(halign, True, True)
        hbox.show()
        self.add(hbox)

        if gtk.widget_get_default_direction() == gtk.TEXT_DIR_RTL:
            hbox.reverse()

        self.connect('enter-notify-event', self.__enter_notify_event_cb)
        self.connect('leave-notify-event', self.__leave_notify_event_cb)

    def __enter_notify_event_cb(self, box, event):
        box.modify_bg(gtk.STATE_NORMAL,
                      style.COLOR_SELECTION_GREY.get_gdk_color())
        return False

    def __leave_notify_event_cb(self, box, event):
        box.modify_bg(gtk.STATE_NORMAL,
                      style.COLOR_PANEL_GREY.get_gdk_color())
        return False
