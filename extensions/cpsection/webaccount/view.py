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

from sugar3.graphics.icon import CanvasIcon, Icon
from sugar3.graphics import style


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
            icon.show()

            label = Gtk.Label()
            label.set_justify(Gtk.Justification.CENTER)
            label.set_markup(
                '<span foreground="%s" size="large">%s</span>'
                % (style.COLOR_BUTTON_GREY.get_html(),
                   GLib.markup_escape_text(
                       _('No web services are installed.\n'
                         'Please visit %s for more details.' %
                         'http://wiki.sugarlabs.org/go/WebServices'))))
            label.show()
            grid.attach(label, 0, 1, 1, 1)

            alignment = Gtk.Alignment.new(0.5, 0.5, 0.1, 0.1)
            alignment.add(grid)
            grid.show()

            self.add(alignment)
            alignment.show()
            return

        grid.set_row_spacing(style.DEFAULT_SPACING * 4)
        grid.set_column_spacing(style.DEFAULT_SPACING * 4)
        grid.set_border_width(style.DEFAULT_SPACING * 2)
        grid.set_column_homogeneous(True)

        width = Gdk.Screen.width() - 2 * style.GRID_CELL_SIZE
        nx = int(width / (style.GRID_CELL_SIZE + style.DEFAULT_SPACING * 4))

        self._service_config_box = Gtk.VBox()

        x = 0
        y = 0
        for service in services:
            service_grid = Gtk.Grid()
            icon = CanvasIcon(icon_name=service.get_icon_name())
            icon.show()
            service_grid.attach(icon, x, y, 1, 1)

            icon.connect('activate', service.config_service_cb, None,
                         self._service_config_box)

            label = Gtk.Label()
            label.set_justify(Gtk.Justification.CENTER)
            name = get_service_name(service)
            label.set_markup(name)
            service_grid.attach(label, x, y + 1, 1, 1)
            label.show()

            grid.attach(service_grid, x, y, 1, 1)
            service_grid.show()

            x += 1
            if x == nx:
                x = 0
                y += 1

        alignment = Gtk.Alignment.new(0.5, 0, 0, 0)
        alignment.add(grid)
        grid.show()

        vbox = Gtk.VBox()
        vbox.pack_start(alignment, False, False, 0)
        alignment.show()

        scrolled = Gtk.ScrolledWindow()
        vbox.pack_start(scrolled, True, True, 0)

        self.add(vbox)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.show()

        workspace = Gtk.VBox()
        scrolled.add_with_viewport(workspace)
        workspace.show()

        workspace.add(self._service_config_box)
        workspace.show_all()
        vbox.show()

    def undo(self):
        pass
