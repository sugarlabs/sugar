# Copyright (C) 2007, Red Hat, Inc.
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
from ConfigParser import ConfigParser
from gettext import gettext as _

import gtk
import gobject
import dbus
import hippo
import logging

from sugar import env
from sugar.graphics import style
from sugar.graphics.canvasbutton import CanvasButton
from sugar.graphics.canvasentry import CanvasEntry

import colorpicker

_BACKGROUND_COLOR = style.COLOR_PANEL_GREY

class _Page(hippo.CanvasBox):
    __gproperties__ = {
        'valid'    : (bool, None, None, False,
                      gobject.PARAM_READABLE)
    }

    def __init__(self, **kwargs):
        hippo.CanvasBox.__init__(self, **kwargs)
        self.valid = False

    def set_valid(self, valid):
        self.valid = valid
        self.notify('valid')

    def do_get_property(self, pspec):
        if pspec.name == 'valid':
            return self.valid

class _NamePage(_Page):
    def __init__(self):
        _Page.__init__(self, xalign=hippo.ALIGNMENT_CENTER,
                       background_color=_BACKGROUND_COLOR.get_int(),
                       spacing=style.DEFAULT_SPACING,
                       orientation=hippo.ORIENTATION_HORIZONTAL,)

        label = hippo.CanvasText(text=_("Name:"))
        self.append(label)

        self._entry = CanvasEntry(box_width=style.zoom(300))
        self._entry.set_background(_BACKGROUND_COLOR.get_html())
        self._entry.props.widget.set_max_length(45)
        self._entry.connect('notify::text', self._text_changed_cb)
        self.append(self._entry)

    def _text_changed_cb(self, entry, pspec):
        valid = len(entry.props.text.strip()) > 0
        self.set_valid(valid)

    def get_name(self):
        return self._entry.props.text

class _ColorPage(_Page):
    def __init__(self, **kwargs):
        _Page.__init__(self, xalign=hippo.ALIGNMENT_CENTER,
                       background_color=_BACKGROUND_COLOR.get_int(),
                       spacing=style.DEFAULT_SPACING,
                       yalign=hippo.ALIGNMENT_CENTER, **kwargs)

        self._label = hippo.CanvasText(text=_("Click to change color:"),
                                       xalign=hippo.ALIGNMENT_CENTER)
        self.append(self._label)

        self._cp = colorpicker.ColorPicker(xalign=hippo.ALIGNMENT_CENTER)
        self.append(self._cp)

        self._color = self._cp.get_color()
        self.set_valid(True)

    def get_color(self):
        return self._cp.get_color()

class _IntroBox(hippo.CanvasBox):
    __gsignals__ = {
        'done': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                 ([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT,
                   gobject.TYPE_PYOBJECT]))
    }

    PAGE_NAME = 0
    PAGE_COLOR = 1

    PAGE_FIRST = PAGE_NAME
    PAGE_LAST = PAGE_COLOR

    def __init__(self):
        hippo.CanvasBox.__init__(self, padding=style.zoom(30),
                                 background_color=_BACKGROUND_COLOR.get_int())

        self._page = self.PAGE_NAME
        self._name_page = _NamePage()
        self._color_page = _ColorPage()
        self._current_page = None

        self._setup_page()

    def _setup_page(self):
        self.remove_all()

        if self._page == self.PAGE_NAME:
            self._current_page = self._name_page
        elif self._page == self.PAGE_COLOR:
            self._current_page = self._color_page

        self.append(self._current_page, hippo.PACK_EXPAND)

        button_box = hippo.CanvasBox(orientation=hippo.ORIENTATION_HORIZONTAL)

        if self._page != self.PAGE_FIRST:
            back_button = CanvasButton(_('Back'), 'go-left')
            back_button.connect('activated', self._back_activated_cb)
            button_box.append(back_button)

        spacer = hippo.CanvasBox()
        button_box.append(spacer, hippo.PACK_EXPAND)

        if self._page == self.PAGE_LAST:
            self._next_button = CanvasButton(_('Done'), 'go-right')
            self._next_button.connect('activated', self._done_activated_cb)
        else:
            self._next_button = CanvasButton(_('Next'), 'go-right')
            self._next_button.connect('activated', self._next_activated_cb)

        self._update_next_button()
        button_box.append(self._next_button)

        self._current_page.connect('notify::valid',
                                   self._page_valid_changed_cb)

        self.append(button_box)

    def _update_next_button(self):
        widget = self._next_button.props.widget
        widget.props.sensitive = self._current_page.props.valid

    def _page_valid_changed_cb(self, page, pspec):
        self._update_next_button()

    def _back_activated_cb(self, item):
        self._page -= 1
        self._setup_page()

    def _next_activated_cb(self, item):
        self._page += 1
        self._setup_page()

    def _done_activated_cb(self, item):
        path = os.path.join(os.path.dirname(__file__), 'default-picture.png')
        pixbuf = gtk.gdk.pixbuf_new_from_file(path)
        name = self._name_page.get_name()
        color = self._color_page.get_color()
        
        self.emit('done', pixbuf, name, color)

class IntroWindow(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self)

        self._canvas = hippo.Canvas()
        self._intro_box = _IntroBox()
        self._intro_box.connect('done', self._done_cb)
        self._canvas.set_root(self._intro_box)

        self.add(self._canvas)
        self._canvas.show()

    def _done_cb(self, box, pixbuf, name, color):
        self.hide()
        gobject.idle_add(self._create_profile, pixbuf, name, color)

    def _create_profile(self, pixbuf, name, color):
        # Save the buddy icon
        icon_path = os.path.join(env.get_profile_path(), "buddy-icon.jpg")
        scaled = pixbuf.scale_simple(200, 200, gtk.gdk.INTERP_BILINEAR)
        pixbuf.save(icon_path, "jpeg", {"quality":"85"})

        cp = ConfigParser()
        section = 'Buddy'
        if not cp.has_section(section):
            cp.add_section(section)
        # encode nickname to ascii-safe characters
        cp.set(section, 'NickName', name.encode("utf-8"))
        cp.set(section, 'Color', color.to_string())

        section = 'Server'
        if not cp.has_section(section):
            cp.add_section(section)
        if env.is_emulator():
            cp.set(section, 'Server', 'olpc.collabora.co.uk')
        else:
            cp.set(section, 'Server', '')
        cp.set(section, 'Registered', 'False')

        config_path = os.path.join(env.get_profile_path(), 'config')
        f = open(config_path, 'w')
        cp.write(f)
        f.close()

        # Generate keypair
        import commands
        keypath = os.path.join(env.get_profile_path(), "owner.key")
        cmd = "ssh-keygen -q -t dsa -f %s -C '' -N ''" % keypath
        (s, o) = commands.getstatusoutput(cmd)
        if s != 0:
            logging.error("Could not generate key pair: %d" % s)

        gtk.main_quit()
        return False


if __name__ == "__main__":
    w = IntroWindow()
    w.show()
    w.connect('destroy', gtk.main_quit)
    gtk.main()
