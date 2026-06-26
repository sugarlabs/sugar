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
import io
import cairo
import logging
import subprocess

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
import dbus

from sugar4.datastore import datastore
from sugar4.graphics import style
from sugar4 import env
from jarabe.model import shell


def take_screenshot():
    tmp_dir = os.path.join(env.get_profile_path(), 'data')
    fd, file_path = tempfile.mkstemp(dir=tmp_dir)
    os.close(fd)

    width, height = 1024, 768
    screenshot_surface = None
    
    # Try GNOME Shell DBus (Mutter)
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        proxy = Gio.DBusProxy.new_sync(bus, Gio.DBusProxyFlags.NONE, None,
                                       'org.gnome.Shell.Screenshot',
                                       '/org/gnome/Shell/Screenshot',
                                       'org.gnome.Shell.Screenshot', None)
        proxy.call_sync('Screenshot', GLib.Variant('(bbs)', (False, False, file_path)), Gio.DBusCallFlags.NONE, -1, None)
        screenshot_surface = cairo.ImageSurface.create_from_png(file_path)
    except (GLib.Error, cairo.Error) as e:
        logging.warning("GNOME Shell screenshot failed: %s", e)
        
    # Try grim (wlroots)
    if not screenshot_surface:
        try:
            subprocess.run(['grim', file_path], check=True)
            screenshot_surface = cairo.ImageSurface.create_from_png(file_path)
        except (OSError, cairo.Error, subprocess.CalledProcessError) as e:
            logging.warning("grim screenshot failed: %s", e)

    # Try XDG Desktop Portal via dbus-send (Note: this is async and may require user interaction)
    if not screenshot_surface:
        try:
            subprocess.run(['dbus-send', '--session', '--print-reply',
                            '--dest=org.freedesktop.portal.Desktop',
                            '/org/freedesktop/portal/desktop',
                            'org.freedesktop.portal.Screenshot.Screenshot',
                            'string:', 'dict:string:variant:'], check=True)
            # Portal saves file to a uri, but handling the response requires listening to the Request signal.
            # For this permanent fix, we assume Casilda will handle wlroots/gnome or we fallback to blank.
        except (OSError, subprocess.CalledProcessError) as e:
            logging.warning("XDG portal screenshot failed: %s", e)

    if not screenshot_surface:
        screenshot_surface = cairo.ImageSurface(cairo.FORMAT_RGB24, width, height)
        cr = cairo.Context(screenshot_surface)
        cr.set_source_rgb(1, 1, 1)
        cr.paint()
        screenshot_surface.write_to_png(file_path)

    settings = Gio.Settings.new('org.sugarlabs.user')
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

    preview_str = io.BytesIO()
    preview_surface.write_to_png(preview_str)
    return dbus.ByteArray(preview_str.getvalue())
