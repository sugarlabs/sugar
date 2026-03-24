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
from gi.repository import Gdk

from sugar4.graphics import style
from sugar4.graphics.icon import Icon

from jarabe.journal.expandedentry import ExpandedEntry
from jarabe.journal import model


_css_added = False


def _add_css():
    global _css_added
    if _css_added:
        return
    _css_added = True
    provider = Gtk.CssProvider()
    provider.load_from_data(b"""
    .backbar-normal { background-color: #808080; }
    .backbar-hover { background-color: #A0A0A0; }
    """)
    display = Gdk.Display.get_default()
    if display:
        Gtk.StyleContext.add_provider_for_display(
            display, provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


class DetailView(Gtk.Box):
    __gtype_name__ = 'DetailView'

    __gsignals__ = {
        'go-back-clicked': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, journalactivity, **kwargs):
        self._journalactivity = journalactivity
        self._metadata = None
        self._expanded_entry = None

        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)

        back_bar = BackBar()
        back_bar.connect_click(self.__back_bar_release_event_cb)
        self.append(back_bar)

    def _fav_icon_activated_cb(self, fav_icon):
        keep = not self._expanded_entry.get_keep()
        self._expanded_entry.set_keep(keep)
        fav_icon.props.keep = keep

    def __back_bar_release_event_cb(self, back_bar):
        self.emit('go-back-clicked')

    def _update_view(self):
        if self._expanded_entry is None:
            self._expanded_entry = ExpandedEntry(self._journalactivity)
            self._expanded_entry.set_hexpand(True)
            self._expanded_entry.set_vexpand(True)
            self.append(self._expanded_entry)
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

    metadata = GObject.Property(
        type=object, getter=get_metadata, setter=set_metadata)


class BackBar(Gtk.Box):

    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.HORIZONTAL)
        self.set_can_target(True)
        self.set_focusable(True)
        self.set_can_focus(True)

        _add_css()
        self.get_style_context().add_class('backbar-normal')

        # Event controller for hover
        motion = Gtk.EventControllerMotion()
        motion.connect('enter', self.__enter_cb)
        motion.connect('leave', self.__leave_cb)
        self.add_controller(motion)

        # Click callback stored for external connection
        self._click_callback = None

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                       spacing=style.DEFAULT_PADDING)
        hbox.set_margin_start(style.DEFAULT_PADDING)
        hbox.set_margin_end(style.DEFAULT_PADDING)
        hbox.set_margin_top(style.DEFAULT_PADDING)
        hbox.set_margin_bottom(style.DEFAULT_PADDING)
        icon = Icon(icon_name='go-previous', pixel_size=style.SMALL_ICON_SIZE,
                    fill_color=style.COLOR_TOOLBAR_GREY.get_svg())
        hbox.append(icon)

        label = Gtk.Label()
        label.set_text(_('Back'))
        label_wrapper = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        label_wrapper.set_halign(Gtk.Align.START)
        label_wrapper.set_valign(Gtk.Align.CENTER)
        label_wrapper.set_vexpand(True)
        label_wrapper.set_hexpand(True)
        label_wrapper.append(label)
        hbox.append(label_wrapper)
        hbox.show()
        self.append(hbox)

        if Gtk.Widget.get_default_direction() == Gtk.TextDirection.RTL:
            # Reverse hbox children.
            child = hbox.get_first_child()
            while child:
                next_sibling = child.get_next_sibling()
                if next_sibling:
                    hbox.insert_child_after(next_sibling, None) # Prepend sibling
                else:
                    break
                # Since we moved next_sibling to front, we don't advance the loop pointer
                # in a way that skips. This is tricky.
                # Actually, if we just want to reverse them once:
                pass
            # Better way: collect and prepend
            children = []
            child = hbox.get_first_child()
            while child:
                children.append(child)
                child = child.get_next_sibling()
            for child in children:
                hbox.insert_child_after(child, None)

    def connect_click(self, callback):
        """Connect a click callback using GTK4 GestureClick."""
        self._click_callback = callback
        gesture = Gtk.GestureClick()
        gesture.connect('released', self.__released_cb)
        self.add_controller(gesture)

    def __released_cb(self, gesture, n_press, x, y):
        if self._click_callback:
            self._click_callback(self)

    def __enter_cb(self, controller, x, y):
        self.get_style_context().remove_class('backbar-normal')
        self.get_style_context().add_class('backbar-hover')

    def __leave_cb(self, controller):
        self.get_style_context().remove_class('backbar-hover')
        self.get_style_context().add_class('backbar-normal')
