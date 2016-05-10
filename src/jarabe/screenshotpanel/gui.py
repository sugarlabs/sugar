#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2016  Utkarsh Tiwari
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
#
# Contact information:
# Utkarsh Tiwari    iamutkarshtiwari@gmail.com

import os
import dbus
import cairo
import logging
import StringIO
import tempfile
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gio

from sugar3 import env

from sugar3.datastore import datastore
from sugar3.graphics.icon import Icon
from sugar3.graphics import style
from sugar3.graphics.alert import Alert, TimeoutAlert
from sugar3.graphics import iconentry


from jarabe.model.session import get_session_manager
from jarabe.screenshotpanel.toolbar import MainToolbar
from jarabe import config
from jarabe.model import shell


_logger = logging.getLogger('ScreenshotPanel')


class ScreenshotPanel(Gtk.Window):
    '''
    Generates a pop papel to allow user to save the
    screenshot by the name of his choice
    '''

    __gtype_name__ = 'ScreenshotPanel'


    def __init__(self):
        Gtk.Window.__init__(self)

        self.modify_bg(Gtk.StateType.NORMAL,
                                  style.COLOR_BLACK.get_gdk_color())
        self._set_screensize()
        self.set_border_width(style.LINE_WIDTH)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_modal(True)
        self.set_can_focus(True)

        self.connect('key-press-event', self.__key_press_event_cb)

        self._toolbar = None
        self._canvas = None
        self._table = None
        self._scrolledwindow = None
        self._separator = None
        self._section_view = None
        self._section_toolbar = None
        self._main_toolbar = None

        self._vbox = Gtk.VBox()
        self._hbox = Gtk.HBox()
        self._vbox.pack_start(self._hbox, True, True, 0)
        self._hbox.show()

        self._main_view = Gtk.EventBox()
        self._hbox.pack_start(self._main_view, True, True, 0)
        self._main_view.modify_bg(Gtk.StateType.NORMAL,
                                  style.COLOR_BLACK.get_gdk_color())
        self._main_view.show()

        self.add(self._vbox)
        self._vbox.show()
        self._setup_main()
        self._show_main_view()

        # Generates the thumbnail
        preview_image, activity_title = generate_thumbnail()
        self._main_view.add(preview_image)
        preview_image.show()
        self.screenshot_surface, self.file_path = take_screenshot()

        self._vbox = Gtk.VBox()
        self._hbox.pack_start(self._vbox, True, True, 0)
        self._vbox.show()

        # Name label
        name_label = Gtk.Label()
        name_label.set_alignment(0.5, 1)
        name_label.set_use_markup(True)
        name_label.set_markup("<b>"+_('Name')+"</b>")
        name_label.modify_bg(Gtk.StateType.NORMAL,
                                  style.COLOR_BLACK.get_gdk_color())
        name_label.modify_fg(Gtk.StateType.NORMAL, Gdk.color_parse("yellow"))
        self._vbox.pack_start(name_label, True, True, 0)
        name_label.show()

        # Name entry box
        self._name_view = Gtk.EventBox()
        self._name_view.modify_bg(Gtk.StateType.NORMAL,
                                  style.COLOR_BLACK.get_gdk_color())
        self._name_view.show()

        # Entry box
        self._search_entry = Gtk.Entry()
        halign = Gtk.Alignment.new(0.5, 1, 0, 0)
        halign.add(self._name_view)
        halign.show()

        self._vbox.pack_start(halign, True, True, 0)
        self._name_view.add(self._search_entry)
        self._search_entry.show()
        self._search_entry.set_text(_(activity_title))

        self._buttons_box = Gtk.HButtonBox()
        self._buttons_box.set_layout(Gtk.ButtonBoxStyle.CENTER)
        self._buttons_box.set_spacing(style.DEFAULT_SPACING)

        _ok = Gtk.Button()
        _ok.set_image(Icon(icon_name='dialog-ok'))
        _ok.set_label(_('Yes'))
        _ok.connect('clicked', self.__ok_clicked_cb)
        self._buttons_box.pack_start(_ok, True, True, 0)
        _ok.show()

        _cancel = Gtk.Button()
        _cancel.set_image(Icon(icon_name='dialog-cancel'))
        _cancel.set_label(_('No'))
        _cancel.connect('clicked', self.__cancel_clicked_cb)
        self._buttons_box.pack_start(_cancel, True, True, 0)
        _cancel.show()

        self._vbox.pack_start(self._buttons_box, True, True, 0)
        self._buttons_box.show()
        self._search_entry.grab_focus()
        self.show()

    def __cancel_clicked_cb(self, widget):
        self.destroy()

    def __ok_clicked_cb(self, widget):
        self.save_screenshot(self._search_entry.get_text())
        self.destroy()

    def _set_cursor(self, cursor):
        self.get_window().set_cursor(cursor)
        Gdk.flush()

    def _set_screensize(self):
        '''
        Sets the size of the popup based on
        the screen resolution.
        '''
        width = Gdk.Screen.width() / 4
        height = Gdk.Screen.height() / 4
        self.set_size_request(width, height)

    def _set_toolbar(self, toolbar):
        '''
        Sets up the toolbar on the popup.
        '''
        if self._toolbar:
            self._vbox.remove(self._toolbar)
        self._vbox.pack_start(toolbar, False, False, 0)
        self._vbox.reorder_child(toolbar, 0)
        self._toolbar = toolbar
        if not self._separator:
            self._separator = Gtk.HSeparator()
            self._vbox.pack_start(self._separator, False, False, 0)
            self._vbox.reorder_child(self._separator, 1)
            self._separator.show()

    def _setup_main(self):
        self._main_toolbar = MainToolbar()

    def _show_main_view(self):
        self._set_toolbar(self._main_toolbar)
        self._main_toolbar.show()
        self._main_view.modify_bg(Gtk.StateType.NORMAL,
                                  style.COLOR_BLACK.get_gdk_color())

    def __key_press_event_cb(self, window, event):
        # if the user clicked out of the window - fix SL #3188
        if not self.is_active():
            self.present()
        return False

    def save_screenshot(self, title):
        settings = Gio.Settings('org.sugarlabs.user')
        color = settings.get_string('color')

        jobject = datastore.create()
        try:
            jobject.metadata['title'] = title
            jobject.metadata['keep'] = '0'
            jobject.metadata['buddies'] = ''
            jobject.metadata['preview'] = _get_preview_data(self.screenshot_surface)
            jobject.metadata['icon-color'] = color
            jobject.metadata['mime_type'] = 'image/png'
            jobject.file_path = self.file_path
            datastore.write(jobject, transfer_ownership=True)
        finally:
            jobject.destroy()
            del jobject


def generate_thumbnail():
    '''
    Generates the thumbnail to be displayed
    on the screenshot alert popup
    '''
    window = Gdk.get_default_root_window()
    width, height = window.get_width(), window.get_height()
    thumb_width, thumb_height = style.zoom(200), style.zoom(160)

    thumb_surface = Gdk.Window.create_similar_surface(
        window, cairo.CONTENT_COLOR, thumb_width, thumb_height)

    cairo_context = cairo.Context(thumb_surface)
    thumb_scale_w = thumb_width * 1.0 / width
    thumb_scale_h = thumb_height * 1.0 / height
    cairo_context.scale(thumb_scale_w, thumb_scale_h)
    Gdk.cairo_set_source_window(cairo_context, window, 0, 0)
    cairo_context.paint()

    link_width, link_height = style.zoom(200), style.zoom(160)
    link_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                      link_width, link_height)

    cairo_context = cairo.Context(link_surface)
    dest_x = style.zoom(0)
    dest_y = style.zoom(0)
    cairo_context.set_source_surface(thumb_surface, dest_x, dest_y)
    thumb_width, thumb_height = style.zoom(200), style.zoom(160)
    cairo_context.rectangle(dest_x, dest_y, thumb_width, thumb_height)
    cairo_context.fill()

    bg_width, bg_height = style.zoom(200), style.zoom(160)
    pixbuf_bg = Gdk.pixbuf_get_from_surface(link_surface, 0, 0,
                                            bg_width, bg_height)

    preview_image = Gtk.Image()
    preview_image.set_from_pixbuf(pixbuf_bg)

    # Set's the default title
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

    return preview_image, title


def take_screenshot():
    '''
    Captures a screenshot and saves
    it to a temp dir.
    '''
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

    return screenshot_surface, file_path


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