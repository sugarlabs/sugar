# Copyright (C) 2008 One Laptop Per Child
# Copyright (C) 2009 Simon Schampijer, James Zaki
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
import tempfile
from gettext import gettext as _
import StringIO
import cairo

from gi.repository import Gdk
from gi.repository import Gio
import dbus

from sugar3.datastore import datastore
from sugar3.graphics import style
from sugar3 import env
from jarabe.model import shell


def take_screenshot():
    tmp_dir = os.path.join(env.get_profile_path(), 'data')
    fd, file_path = tempfile.mkstemp(dir=tmp_dir)
    os.close(fd)

    window = Gdk.get_default_root_window()
    width, height = window.get_width(), window.get_height()

    screenshot_surface = Gdk.Window.create_similar_surface(
        window, cairo.CONTENT_COLOR, width, height)

    cr = cairo.Context(screenshot_surface)
    Gdk.cairo_set_source_window(cr, window, 0, 0)
    cr.paint()
    screenshot_surface.write_to_png(file_path)

    settings = Gio.Settings('org.sugarlabs.user')
    color = settings.get_string('color')

    content_title = None
    shell_model = shell.get_model()
    zoom_level = shell_model.zoom_level

    # TRANS: Nouns of what a screenshot contains
    if zoom_level == shell_model.ZOOM_MESH:
        content_title = _('Mesh')
    elif zoom_level == shell_model.ZOOM_GROUP:
        content_title = _('Group')
    elif zoom_level == shell_model.ZOOM_HOME:
        content_title = _('Home')
    elif zoom_level == shell_model.ZOOM_ACTIVITY:
        activity = shell_model.get_active_activity()
        if activity is not None:
            content_title = activity.get_title()
            if content_title is None:
                content_title = _('Activity')

    if content_title is None:
        title = _('Screenshot')
    else:
        title = _('Screenshot of \"%s\"') % content_title

    jobject = datastore.create()
    try:
        jobject.metadata['title'] = title
        jobject.metadata['keep'] = '0'
        jobject.metadata['buddies'] = ''
        jobject.metadata['preview'] = _get_preview_data(screenshot_surface)
        jobject.metadata['icon-color'] = color
        jobject.metadata['mime_type'] = 'image/png'
        jobject.file_path = file_path
        datastore.write(jobject, transfer_ownership=True)
    finally:
        jobject.destroy()
        del jobject

    return title


def _get_preview_data(screenshot_surface):
    screenshot_width = screenshot_surface.get_width()
    screenshot_height = screenshot_surface.get_height()

    preview_width, preview_height = style.zoom(300), style.zoom(225)
    preview_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                         preview_width, preview_height)
    cr = cairo.Context(preview_surface)

    scale_w = preview_width * 1.0 / screenshot_width
    scale_h = preview_height * 1.0 / screenshot_height
    scale = min(scale_w, scale_h)

    translate_x = int((preview_width - (screenshot_width * scale)) / 2)
    translate_y = int((preview_height - (screenshot_height * scale)) / 2)

    cr.translate(translate_x, translate_y)
    cr.scale(scale, scale)

    cr.set_source_rgba(1, 1, 1, 0)
    cr.set_operator(cairo.OPERATOR_SOURCE)
    cr.paint()
    cr.set_source_surface(screenshot_surface)
    cr.paint()

    preview_str = StringIO.StringIO()
    preview_surface.write_to_png(preview_str)
    return dbus.ByteArray(preview_str.getvalue())
