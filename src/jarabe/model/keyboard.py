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
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib


def setup():
    settings = Gio.Settings.new('org.sugarlabs.peripherals.keyboard')
    have_config = False
    try:

        layouts = settings.get_strv('layouts')
        layouts_list = []
        variants_list = []
        if layouts:
            for layout in layouts:
                if '(' in layout and layout.endswith(')'):
                    layouts_list.append(layout.split('(')[0])
                    variants_list.append(layout.split('(')[1][:-1])
                else:
                    layouts_list.append(layout)
                    variants_list.append('')

            if layouts_list:
                have_config = True

        model = settings.get_string('model')
        if model:
            have_config = True

        options = settings.get_strv('options')
        if options:
            have_config = True

        if have_config:
            bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
            proxy = Gio.DBusProxy.new_sync(bus, Gio.DBusProxyFlags.NONE, None,
                                           'org.freedesktop.locale1',
                                           '/org/freedesktop/locale1',
                                           'org.freedesktop.locale1', None)
            layouts_str = ",".join(layouts_list)
            variants_str = ",".join(variants_list)
            options_str = ",".join(options) if options else ""
            proxy.call_sync('SetX11Keyboard',
                            GLib.Variant('(ssssb)', (layouts_str, model if model else "", variants_str, options_str, True)),
                            Gio.DBusCallFlags.NONE, -1, None)
    except (GLib.Error, ValueError, IndexError) as e:
        logging.exception('Error during keyboard configuration: %s', e)
