# Copyright (C) 2008 One Laptop Per Child
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

from gi.repository import Gtk
from gi.repository import Gdk
from gettext import gettext as _

from sugar4.graphics.icon import Icon
from sugar4.graphics import style
from sugar4 import profile


_css_modal_added = False


def _add_css_modal():
    global _css_modal_added
    if _css_modal_added:
        return
    _css_modal_added = True
    provider = Gtk.CssProvider()
    provider.load_from_data(b'.modal-alert-bg { background-color: black; }')
    display = Gdk.Display.get_default()
    if display:
        Gtk.StyleContext.add_provider_for_display(
            display, provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


class ModalAlert(Gtk.Window):

    __gtype_name__ = 'SugarModalAlert'

    def __init__(self):
        Gtk.Window.__init__(self)

        self.set_border_width(style.LINE_WIDTH)
        offset = style.GRID_CELL_SIZE
        width = 800 - offset * 2
        height = 600 - offset * 2
        display = Gdk.Display.get_default()
        if display:
            monitors = display.get_monitors()
            if monitors.get_n_items() > 0:
                monitor = monitors.get_item(0)
                geometry = monitor.get_geometry()
                width = geometry.width - offset * 2
                height = geometry.height - offset * 2
        self.set_size_request(width, height)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_modal(True)

        self._main_view = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._vbox.set_spacing(style.DEFAULT_SPACING)
        self._vbox.set_margin_start(style.GRID_CELL_SIZE * 2)
        self._vbox.set_margin_end(style.GRID_CELL_SIZE * 2)
        self._vbox.set_margin_top(style.GRID_CELL_SIZE * 2)
        self._vbox.set_margin_bottom(style.GRID_CELL_SIZE * 2)
        _add_css_modal()
        self._main_view.get_style_context().add_class('modal-alert-bg')
        self._main_view.append(self._vbox)
        self._vbox.show()

        color = profile.get_color()

        icon = Icon(icon_name='activity-journal',
                    pixel_size=style.XLARGE_ICON_SIZE,
                    xo_color=color)
        self._vbox.pack_start(icon, expand=False, fill=False, padding=0)
        icon.show()

        self._title = Gtk.Label()
        self._title.modify_fg(Gtk.StateType.NORMAL,
                              style.COLOR_WHITE.get_gdk_color())
        self._title.set_markup('<b>%s</b>' % _('Your Journal is full'))
        self._vbox.pack_start(self._title, expand=False, fill=False, padding=0)
        self._title.show()

        self._message = Gtk.Label(
            label=_('Please delete some old Journal'
                    ' entries to make space for new ones.'))
        self._message.modify_fg(Gtk.StateType.NORMAL,
                                style.COLOR_WHITE.get_gdk_color())
        self._vbox.pack_start(self._message, expand=False,
                              fill=False, padding=0)
        self._message.show()

        btn_wrapper = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        btn_wrapper.set_halign(Gtk.Align.CENTER)
        btn_wrapper.set_valign(Gtk.Align.CENTER)
        self._vbox.pack_start(btn_wrapper, expand=False, fill=True, padding=0)
        btn_wrapper.show()

        self._show_journal = Gtk.Button()
        self._show_journal.set_label(_('Show Journal'))
        btn_wrapper.append(self._show_journal)
        self._show_journal.show()
        self._show_journal.connect('clicked', self.__show_journal_cb)

        self.add(self._main_view)
        self._main_view.show()

        self.connect('realize', self.__realize_cb)

    def __realize_cb(self, widget):
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.get_window().set_accept_focus(True)

    def __show_journal_cb(self, button):
        """The opener will listen on the destroy signal"""
        self.destroy()
