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
from gi.repository import GLib
from gettext import gettext as _

from sugar4.graphics.icon import Icon
from sugar4.graphics import style
from sugar4 import profile
from jarabe.model import shell


class ModalAlert(Gtk.Window):

    __gtype_name__ = 'SugarModalAlert'

    def __init__(self):
        super().__init__()

        offset = style.GRID_CELL_SIZE
        
        # Calculate dynamic size based on primary monitor geometry
        display = Gdk.Display.get_default()
        monitor = display.get_monitors().get_item(0)
        if monitor is not None:
            geometry = monitor.get_geometry()
            width = geometry.width - offset * 2
            height = geometry.height - offset * 2
            self.set_default_size(width, height)
        else:
            self.set_default_size(800, 600)
        
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_modal(True)

        # Set transient parent window
        shell_model = shell.get_model()
        if shell_model and shell_model._main_window:
            self.set_transient_for(shell_model._main_window)

        # Key controller: Escape closes
        key_controller = Gtk.EventControllerKey()
        key_controller.connect('key-pressed', self.__key_press_event_cb)
        self.add_controller(key_controller)

        self._main_view = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        # Apply black background CSS
        self._main_view.add_css_class('modal-bg')

        self._vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._vbox.set_spacing(style.DEFAULT_SPACING)
        self._vbox.set_margin_top(style.GRID_CELL_SIZE * 2)
        self._vbox.set_margin_bottom(style.GRID_CELL_SIZE * 2)
        self._vbox.set_margin_start(style.GRID_CELL_SIZE * 2)
        self._vbox.set_margin_end(style.GRID_CELL_SIZE * 2)

        self._main_view.append(self._vbox)
        self._vbox.set_visible(True)

        color = profile.get_color()

        icon = Icon(icon_name='activity-journal',
                    pixel_size=style.XLARGE_ICON_SIZE,
                    xo_color=color)
        self._vbox.append(icon)
        icon.set_visible(True)

        self._title = Gtk.Label()
        self._title.set_markup('<b>%s</b>' % _('Your Journal is full'))
        self._vbox.append(self._title)
        self._title.set_visible(True)

        self._message = Gtk.Label(
            label=_('Please delete some old Journal'
                    ' entries to make space for new ones.'))
        self._vbox.append(self._message)
        self._message.set_visible(True)

        # Alignment can be replaced by Box with hexpand/vexpand
        alignment = Gtk.Box()
        alignment.set_hexpand(True)
        alignment.set_vexpand(True)
        alignment.set_halign(Gtk.Align.CENTER)
        alignment.set_valign(Gtk.Align.CENTER)
        self._vbox.append(alignment)
        alignment.set_visible(True)

        self._show_journal = Gtk.Button()
        self._show_journal.set_label(_('Show Journal'))
        alignment.append(self._show_journal)
        self._show_journal.set_visible(True)
        self._show_journal.connect('clicked', self.__show_journal_cb)

        self.set_child(self._main_view)
        self._main_view.set_visible(True)

        self.connect('realize', self.__realize_cb)

    def __realize_cb(self, widget):
        self.set_focusable(True)
        shell.get_model().push_modal()

    def __key_press_event_cb(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            shell.get_model().pop_modal()
            self.close()
            return True
        return False

    def __show_journal_cb(self, button):
        """The opener will listen on the close-request signal"""
        shell.get_model().pop_modal()
        self.close()
