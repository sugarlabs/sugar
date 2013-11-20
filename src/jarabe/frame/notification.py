# Copyright (C) 2008 One Laptop Per Child
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

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk

from sugar3.graphics import style
from sugar3.graphics.xocolor import XoColor

from jarabe.view.pulsingicon import PulsingIcon


class NotificationIcon(Gtk.EventBox):
    __gtype_name__ = 'SugarNotificationIcon'

    __gproperties__ = {
        'xo-color': (object, None, None, GObject.PARAM_READWRITE),
        'icon-name': (str, None, None, None, GObject.PARAM_READWRITE),
        'icon-filename': (str, None, None, None, GObject.PARAM_READWRITE),
    }

    _PULSE_TIMEOUT = 3

    def __init__(self, **kwargs):
        self._icon = PulsingIcon(pixel_size=style.STANDARD_ICON_SIZE)
        Gtk.EventBox.__init__(self, **kwargs)
        self.props.visible_window = False

        self._icon.props.pulse_color = \
            XoColor('%s,%s' % (style.COLOR_BUTTON_GREY.get_svg(),
                               style.COLOR_TRANSPARENT.get_svg()))
        self._icon.props.pulsing = True
        self.add(self._icon)
        self._icon.show()

        GObject.timeout_add_seconds(self._PULSE_TIMEOUT,
                                    self.__stop_pulsing_cb)

        self.set_size_request(style.GRID_CELL_SIZE, style.GRID_CELL_SIZE)

    def __stop_pulsing_cb(self):
        self._icon.props.pulsing = False
        return False

    def do_set_property(self, pspec, value):
        if pspec.name == 'xo-color':
            if self._icon.props.base_color != value:
                self._icon.props.base_color = value
        elif pspec.name == 'icon-name':
            if self._icon.props.icon_name != value:
                self._icon.props.icon_name = value
        elif pspec.name == 'icon-filename':
            if self._icon.props.file != value:
                self._icon.props.file = value

    def do_get_property(self, pspec):
        if pspec.name == 'xo-color':
            return self._icon.props.base_color
        elif pspec.name == 'icon-name':
            return self._icon.props.icon_name
        elif pspec.name == 'icon-filename':
            return self._icon.props.file

    def _set_palette(self, palette):
        self._icon.palette = palette

    def _get_palette(self):
        return self._icon.palette

    palette = property(_get_palette, _set_palette)


class NotificationWindow(Gtk.Window):
    __gtype_name__ = 'SugarNotificationWindow'

    def __init__(self, **kwargs):

        Gtk.Window.__init__(self, **kwargs)

        self.set_decorated(False)
        self.set_resizable(False)
        self.connect('realize', self._realize_cb)

    def _realize_cb(self, widget):
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.get_window().set_accept_focus(False)

        color = Gdk.color_parse(style.COLOR_TOOLBAR_GREY.get_html())
        self.modify_bg(Gtk.StateType.NORMAL, color)
