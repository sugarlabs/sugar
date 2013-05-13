# Copyright (C) 2012 Agustin Zubiaga <aguz@sugarlabs.org>
# Copyright (C) 2013 Sugar Labs
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

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import os
import logging

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GConf

BACKGROUND_STRING = '/desktop/sugar/user/background'
BACKGROUND_IMAGE_PATH_STRING = BACKGROUND_STRING + '/image-path'
BACKGROUND_ALPHA_LEVEL_STRING = BACKGROUND_STRING + '/alpha-level'
DEFAULT_BACKGROUND_ALPHA_LEVEL = 0.20


def get_background_image_path():
    client = GConf.Client.get_default()
    path = client.get_string(BACKGROUND_IMAGE_PATH_STRING)
    if path is None:
        return ''
    return path


def get_background_alpha_level():
    client = GConf.Client.get_default()
    alpha = client.get_string(BACKGROUND_ALPHA_LEVEL_STRING)
    if alpha is None:
        alpha = DEFAULT_BACKGROUND_ALPHA_LEVEL
    else:
        try:
            alpha = float(alpha)
        except ValueError:
            alpha = DEFAULT_BACKGROUND_ALPHA_LEVEL
        if alpha < 0:
            alpha = 0
        elif alpha > 1.0:
            alpha = 1.0
    return alpha


class HomeBackgroundBox(Gtk.VBox):
    def __init__(self):
        Gtk.VBox.__init__(self)
        self._background_pixbuf = None
        self._update_background_image()
        self.connect('draw', self.__draw_cb)

        client = GConf.Client.get_default()
        client.add_dir(BACKGROUND_STRING, GConf.ClientPreloadType.PRELOAD_NONE)
        self._gconf_id = client.notify_add(BACKGROUND_STRING,
                                           self.__gconf_changed_cb, None)

    def __del__(self):
        client = GConf.Client.get_default()
        client.notify_remove(self._gconf_id)

    def __draw_cb(self, widget, context):
        if self._background_pixbuf is None:
            return

        alloc = widget.get_allocation()

        if self._background_pixbuf.get_width() != alloc.width or \
                self._background_pixbuf.get_height() != alloc.height:
            self._background_pixbuf = self._background_pixbuf.scale_simple(
                alloc.width,
                alloc.height,
                GdkPixbuf.InterpType.TILES)
        Gdk.cairo_set_source_pixbuf(context, self._background_pixbuf, 0, 0)
        alpha = get_background_alpha_level()
        context.paint_with_alpha(alpha)

    def __gconf_changed_cb(self, client, timestamp, entry, *extra):
        self._update_background_image()
        self.queue_draw()

    def _update_background_image(self, *args):
        background_image_path = get_background_image_path()

        if background_image_path == '':
            self._background_pixbuf = None
        elif os.path.exists(background_image_path):
            try:
                self._background_pixbuf = GdkPixbuf.Pixbuf.new_from_file(
                    background_image_path)
            except Exception as e:
                logging.exception('Failed to update background image %s: %s' %
                                 (background_image_path, str(e)))
                self._background_pixbuf = None
