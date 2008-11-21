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

import os
import tempfile
import time
from gettext import gettext as _

import gtk
import gconf
import dbus

from sugar.datastore import datastore
from sugar.graphics import style

BOUND_KEYS = ['<alt>1']

def handle_key_press(key):
    file_path = os.path.join(tempfile.gettempdir(), '%i' % time.time())

    window = gtk.gdk.get_default_root_window()
    width, height = window.get_size()
    x_orig, y_orig = window.get_origin()

    screenshot = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, has_alpha=False,
                                    bits_per_sample=8, width=width,
                                    height=height)
    screenshot.get_from_drawable(window, window.get_colormap(), x_orig,
                                    y_orig, 0, 0, width, height)
    screenshot.save(file_path, "png")

    client = gconf.client_get_default()
    color = client.get_string('/desktop/sugar/user/color')

    jobject = datastore.create()
    try:
        jobject.metadata['title'] = _('Screenshot')
        jobject.metadata['keep'] = '0'
        jobject.metadata['buddies'] = ''
        jobject.metadata['preview'] = _get_preview_data(screenshot)
        jobject.metadata['icon-color'] = color
        jobject.metadata['mime_type'] = 'image/png'
        jobject.file_path = file_path
        datastore.write(jobject, transfer_ownership=True)
    finally:
        jobject.destroy()
        del jobject

def _get_preview_data(screenshot):
    preview = screenshot.scale_simple(style.zoom(300), style.zoom(225),
                                      gtk.gdk.INTERP_BILINEAR)
    preview_data = []
    def save_func(buf, data):
        data.append(buf)

    preview.save_to_callback(save_func, 'png', user_data=preview_data)

    return dbus.ByteArray(''.join(preview_data))

