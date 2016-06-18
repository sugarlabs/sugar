# Copyright (C) 2007, One Laptop Per Child
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Gtk

from sugar3.graphics import style
from sugar3.graphics.icon import Icon

from jarabe.journal.expandedentry import ExpandedEntry
from jarabe.journal import model


class DetailView(Gtk.VBox):
    __gtype_name__ = 'DetailView'

    __gsignals__ = {
        'go-back-clicked': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, journalactivity, **kwargs):
        self._journalactivity = journalactivity
        self._metadata = None
        self._expanded_entry = None

        Gtk.VBox.__init__(self)

        back_bar = BackBar()
        back_bar.connect('button-release-event',
                         self.__back_bar_release_event_cb)
        self.pack_start(back_bar, False, True, 0)

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
            self._expanded_entry = ExpandedEntry(self._journalactivity)
            self.pack_start(self._expanded_entry, True, True, 0)
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

    metadata = GObject.property(
        type=object, getter=get_metadata, setter=set_metadata)


class BackBar(Gtk.EventBox):

    def __init__(self):
        Gtk.EventBox.__init__(self)
        self.modify_bg(Gtk.StateType.NORMAL,
                       style.COLOR_PANEL_GREY.get_gdk_color())
        hbox = Gtk.HBox(spacing=style.DEFAULT_PADDING)
        hbox.set_border_width(style.DEFAULT_PADDING)
        icon = Icon(icon_name='go-previous', pixel_size=style.SMALL_ICON_SIZE,
                    fill_color=style.COLOR_TOOLBAR_GREY.get_svg())
        hbox.pack_start(icon, False, False, 0)

        label = Gtk.Label()
        label.set_text(_('Back'))
        halign = Gtk.Alignment.new(0, 0.5, 0, 1)
        halign.add(label)
        hbox.pack_start(halign, True, True, 0)
        hbox.show()
        self.add(hbox)

        if Gtk.Widget.get_default_direction() == Gtk.TextDirection.RTL:
            # Reverse hbox children.
            for child in hbox.get_children():
                hbox.reorder_child(child, 0)

        self.connect('enter-notify-event', self.__enter_notify_event_cb)
        self.connect('leave-notify-event', self.__leave_notify_event_cb)

    def __enter_notify_event_cb(self, box, event):
        box.modify_bg(Gtk.StateType.NORMAL,
                      style.COLOR_SELECTION_GREY.get_gdk_color())
        return False

    def __leave_notify_event_cb(self, box, event):
        box.modify_bg(Gtk.StateType.NORMAL,
                      style.COLOR_PANEL_GREY.get_gdk_color())
        return False
