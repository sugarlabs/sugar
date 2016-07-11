# Copyright (C) 2006, Red Hat, Inc.
# Copyright (C) 2009, One Laptop Per Child Association Inc
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

import gi
gi.require_version('Xkl', '1.0')
from gi.repository import Gio
from gi.repository import GdkX11
from gi.repository import Xkl


def setup():
    settings = Gio.Settings('org.sugarlabs.peripherals.keyboard')
    have_config = False

    try:
        display = GdkX11.x11_get_default_xdisplay()
        if display is not None:
            engine = Xkl.Engine.get_instance(display)
        else:
            logging.debug('setup_keyboard_cb: Could not get default display.')
            return

        configrec = Xkl.ConfigRec()
        configrec.get_from_server(engine)

        layouts = settings.get_strv('layouts')
        layouts_list = []
        variants_list = []
        if layouts:
            for layout in layouts:
                layouts_list.append(layout.split('(')[0])
                variants_list.append(layout.split('(')[1][:-1])

            if layouts_list and variants_list:
                have_config = True
                configrec.set_layouts(layouts_list)
                configrec.set_variants(variants_list)

        model = settings.get_string('model')
        if model:
            have_config = True
            configrec.set_model(model)

        options = settings.get_strv('options')
        if options:
            have_config = True
            configrec.set_options(options)

        if have_config:
            configrec.activate(engine)
    except Exception:
        logging.exception('Error during keyboard configuration')
