# Copyright (C) 2013, Walter Bender - Raul Gutierrez Segales
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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

import os
import logging
from importlib import import_module

from gi.repository import Gtk
from gettext import gettext as _

from jarabe.webservice.accountsmanager import get_webaccount_paths
from jarabe.controlpanel.sectionview import SectionView

from sugar3.graphics.icon import CanvasIcon
from sugar3.graphics import style


class WebServicesConfig(SectionView):
    def __init__(self, model, alerts):
        SectionView.__init__(self)

        self._model = model
        self.restart_alerts = alerts

        services = _get_services()
        if len(services) == 0:
            label = Gtk.Label(_('No web services are installed.\n\
Please visit http://wiki.sugarlabs.org/go/WebServices for more details.'))
            label.show()
            self.add(label)
            return

        vbox = Gtk.VBox()
        hbox = Gtk.HBox(style.DEFAULT_SPACING)

        self._service_config_box = Gtk.VBox()

        for service in services:
            icon = CanvasIcon(icon_name=service.get_icon_name())
            icon.connect('button_press_event',
                         service.config_service_cb,
                         self._service_config_box)
            icon.show()
            hbox.pack_start(icon, False, False, 0)

        hbox.show()
        vbox.pack_start(hbox, False, False, 0)

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


def _get_services():
    service_paths = []
    for path in get_webaccount_paths():
        service_paths.append(os.path.join(path, 'services'))

    services = []
    for service_path in service_paths:
        if not os.path.exists(service_path):
            continue

        folders = os.listdir(service_path)
        for folder in folders:
            if not os.path.isdir(os.path.join(service_path, folder)):
                continue

            if not os.path.exists(os.path.join(
                    service_path, folder, 'service.py')):
                continue

            mod = _load_module(os.path.join(service_path, folder),
                               'service')
            if hasattr(mod, 'get_service'):
                services.append(mod.get_service())

    return services


def _load_module(path, module):
    try:
        module = import_module(_convert_path_to_module_name(path, module),
                               [module])
    except ImportError, e:
        module = None
        logging.debug('ImportError: %s' % (e))

    return module


def _convert_path_to_module_name(path, module):
    if 'extensions' not in path:
        return ''

    parts = []
    while 'extensions' not in parts:
        path, base = os.path.split(path)
        parts.append(base)

    parts.reverse()

    return '%s.%s' % ('.'.join(parts[1:]), module)
