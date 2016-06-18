# Copyright (C) 2012 Agustin Zubiaga <aguz@sugarlabs.org>
# Copyright (C) 2013 Sugar Labs
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

import os
import logging

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gio

BACKGROUND_DIR = 'org.sugarlabs.user.background'
BACKGROUND_IMAGE_PATH_KEY = 'image-path'
BACKGROUND_ALPHA_LEVEL_KEY = 'alpha-level'
DEFAULT_BACKGROUND_ALPHA_LEVEL = 0.20


def get_background_image_path():
    settings = Gio.Settings(BACKGROUND_DIR)
    path = settings.get_string(BACKGROUND_IMAGE_PATH_KEY)
    if path is None:
        return ''
    return path


def get_background_alpha_level():
    settings = Gio.Settings(BACKGROUND_DIR)
    alpha = settings.get_string(BACKGROUND_ALPHA_LEVEL_KEY)
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

        self._settings = Gio.Settings(BACKGROUND_DIR)
        self._settings.connect('changed', self.__conf_changed_cb, None)

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

    def __conf_changed_cb(self, settings, key, data):
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
