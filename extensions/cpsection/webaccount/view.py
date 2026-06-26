# Copyright (C) 2013, Walter Bender - Raul Gutierrez Segales
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

from gettext import gettext as _

from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gdk

from jarabe.webservice.accountsmanager import get_webaccount_services
from jarabe.controlpanel.sectionview import SectionView

from sugar4.graphics.icon import CanvasIcon, Icon
from sugar4.graphics import style


def get_service_name(service):
    if hasattr(service, '_account'):
        if hasattr(service._account, 'get_description'):
            return service._account.get_description()
    return ''


class WebServicesConfig(SectionView):
    def __init__(self, model, alerts):
        SectionView.__init__(self)

        self._model = model
        self.restart_alerts = alerts

        services = get_webaccount_services()

        grid = Gtk.Grid()

        if len(services) == 0:
            grid.set_row_spacing(style.DEFAULT_SPACING)

            icon = Icon(pixel_size=style.LARGE_ICON_SIZE,
                        icon_name='module-webaccount',
                        stroke_color=style.COLOR_BUTTON_GREY.get_svg(),
                        fill_color=style.COLOR_TRANSPARENT.get_svg())

            grid.attach(icon, 0, 0, 1, 1)

            label = Gtk.Label()
            label.set_justify(Gtk.Justification.CENTER)
            label.set_markup(
                '<span foreground="%s" size="large">%s</span>'
                % (style.COLOR_BUTTON_GREY.get_html(),
                   GLib.markup_escape_text(
                       _('No web services are installed.\n'
                         'Please visit %s for more details.' %
                         'http://wiki.sugarlabs.org/go/WebServices'))))
            grid.attach(label, 0, 1, 1, 1)

            grid.set_halign(Gtk.Align.CENTER)
            grid.set_valign(Gtk.Align.CENTER)
            grid.set_hexpand(True)
            grid.set_vexpand(True)
            
            self.append(grid)
            return

        grid.set_row_spacing(style.DEFAULT_SPACING * 4)
        grid.set_column_spacing(style.DEFAULT_SPACING * 4)
        grid.set_margin_start(style.DEFAULT_SPACING * 2)
        grid.set_margin_end(style.DEFAULT_SPACING * 2)
        grid.set_margin_top(style.DEFAULT_SPACING * 2)
        grid.set_margin_bottom(style.DEFAULT_SPACING * 2)
        grid.set_column_homogeneous(True)

        width = 800 - 2 * style.GRID_CELL_SIZE
        nx = int(width / (style.GRID_CELL_SIZE + style.DEFAULT_SPACING * 4))

        self._service_config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        x = 0
        y = 0
        for service in services:
            service_grid = Gtk.Grid()
            icon = CanvasIcon(icon_name=service.get_icon_name())
            service_grid.attach(icon, 0, 0, 1, 1)

            gesture = Gtk.GestureClick()
            gesture.connect('pressed', self._on_service_clicked, service)
            icon.add_controller(gesture)

            label = Gtk.Label()
            label.set_justify(Gtk.Justification.CENTER)
            name = get_service_name(service)
            label.set_markup(name)
            service_grid.attach(label, 0, 1, 1, 1)

            grid.attach(service_grid, x, y, 1, 1)

            x += 1
            if x == nx:
                x = 0
                y += 1

        grid.set_halign(Gtk.Align.CENTER)
        grid.set_valign(Gtk.Align.START)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.append(grid)

        scrolled = Gtk.ScrolledWindow()
        vbox.append(scrolled)
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)

        self.append(vbox)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        workspace = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scrolled.set_child(workspace)

        workspace.append(self._service_config_box)

    def undo(self):
        pass

    def _on_service_clicked(self, gesture, n_press, x, y, service):
        service.config_service_cb(gesture.get_widget(), None, self._service_config_box)
