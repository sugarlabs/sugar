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
import os.path
import logging
from gettext import gettext as _
import gconf
import pwd

import gtk
import gobject

from sugar import env
from sugar import profile
from sugar.graphics import style
from sugar.graphics.icon import Icon
from sugar.graphics.xocolor import XoColor

from jarabe.intro import colorpicker


_BACKGROUND_COLOR = style.COLOR_WHITE


def create_profile(name, color=None):
    if not color:
        color = XoColor()

    client = gconf.client_get_default()
    client.set_string('/desktop/sugar/user/nick', name)
    client.set_string('/desktop/sugar/user/color', color.to_string())
    client.suggest_sync()

    if profile.get_pubkey() and profile.get_profile().privkey_hash:
        logging.info('Valid key pair found, skipping generation.')
        return

    # Generate keypair
    import commands
    keypath = os.path.join(env.get_profile_path(), 'owner.key')
    if os.path.exists(keypath):
        os.rename(keypath, keypath + '.broken')
        logging.warning('Existing private key %s moved to %s.broken',
                        keypath, keypath)

    if os.path.exists(keypath + '.pub'):
        os.rename(keypath + '.pub', keypath + '.pub.broken')
        logging.warning('Existing public key %s.pub moved to %s.pub.broken',
                        keypath, keypath)

    cmd = "ssh-keygen -q -t dsa -f %s -C '' -N ''" % (keypath, )
    (s, o) = commands.getstatusoutput(cmd)
    if s != 0:
        logging.error('Could not generate key pair: %d %s', s, o)


class _Page(gtk.VBox):
    __gproperties__ = {
        'valid': (bool, None, None, False, gobject.PARAM_READABLE),
    }

    def __init__(self):
        gtk.VBox.__init__(self)
        self.valid = False

    def set_valid(self, valid):
        self.valid = valid
        self.notify('valid')

    def do_get_property(self, pspec):
        if pspec.name == 'valid':
            return self.valid

    def activate(self):
        pass


class _NamePage(_Page):
    def __init__(self, intro):
        _Page.__init__(self)
        self._intro = intro

        alignment = gtk.Alignment(0.5, 0.5, 0, 0)
        self.pack_start(alignment, expand=True, fill=True)

        hbox = gtk.HBox(spacing=style.DEFAULT_SPACING)
        alignment.add(hbox)

        label = gtk.Label(_('Name:'))
        hbox.pack_start(label, expand=False)

        self._entry = gtk.Entry()
        self._entry.connect('notify::text', self._text_changed_cb)
        self._entry.set_size_request(style.zoom(300), -1)
        self._entry.set_max_length(45)
        hbox.pack_start(self._entry, expand=False)

    def _text_changed_cb(self, entry, pspec):
        valid = len(entry.props.text.strip()) > 0
        self.set_valid(valid)

    def get_name(self):
        return self._entry.props.text

    def set_name(self, new_name):
        self._entry.props.text = new_name

    def activate(self):
        self._entry.grab_focus()


class _ColorPage(_Page):
    def __init__(self):
        _Page.__init__(self)

        vbox = gtk.VBox(spacing=style.DEFAULT_SPACING)
        self.pack_start(vbox, expand=True, fill=False)

        self._label = gtk.Label(_('Click to change color:'))
        vbox.pack_start(self._label)

        self._cp = colorpicker.ColorPicker()
        vbox.pack_start(self._cp)

        self._color = self._cp.get_color()
        self.set_valid(True)

    def get_color(self):
        return self._cp.get_color()


class _IntroBox(gtk.VBox):
    __gsignals__ = {
        'done': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                 ([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT])),
    }

    PAGE_NAME = 0
    PAGE_COLOR = 1

    PAGE_FIRST = PAGE_NAME
    PAGE_LAST = PAGE_COLOR

    def __init__(self):
        gtk.VBox.__init__(self)
        self.set_border_width(style.zoom(30))

        self._page = self.PAGE_NAME
        self._name_page = _NamePage(self)
        self._color_page = _ColorPage()
        self._current_page = None
        self._next_button = None

        client = gconf.client_get_default()
        default_nick = client.get_string('/desktop/sugar/user/default_nick')
        if default_nick != 'disabled':
            self._page = self.PAGE_COLOR
            if default_nick == 'system':
                pwd_entry = pwd.getpwuid(os.getuid())
                default_nick = (pwd_entry.pw_gecos.split(',')[0] or
                                pwd_entry.pw_name)
            self._name_page.set_name(default_nick)

        self._setup_page()

    def _setup_page(self):
        for child in self.get_children():
            self.remove(child)

        if self._page == self.PAGE_NAME:
            self._current_page = self._name_page
        elif self._page == self.PAGE_COLOR:
            self._current_page = self._color_page

        self.pack_start(self._current_page, expand=True)

        button_box = gtk.HButtonBox()

        if self._page == self.PAGE_FIRST:
            button_box.set_layout(gtk.BUTTONBOX_END)
        else:
            button_box.set_layout(gtk.BUTTONBOX_EDGE)
            back_button = gtk.Button(_('Back'))
            image = Icon(icon_name='go-left')
            back_button.set_image(image)
            back_button.connect('clicked', self._back_activated_cb)
            button_box.pack_start(back_button)

        self._next_button = gtk.Button()
        image = Icon(icon_name='go-right')
        self._next_button.set_image(image)

        if self._page == self.PAGE_LAST:
            self._next_button.set_label(_('Done'))
            self._next_button.connect('clicked', self._done_activated_cb)
        else:
            self._next_button.set_label(_('Next'))
            self._next_button.connect('clicked', self._next_activated_cb)

        self._current_page.activate()

        self._update_next_button()
        button_box.pack_start(self._next_button)

        self._current_page.connect('notify::valid',
                                   self._page_valid_changed_cb)

        self.pack_start(button_box, expand=False)
        self.show_all()

    def _update_next_button(self):
        self._next_button.set_sensitive(self._current_page.props.valid)

    def _page_valid_changed_cb(self, page, pspec):
        self._update_next_button()

    def _back_activated_cb(self, widget):
        self.back()

    def back(self):
        if self._page != self.PAGE_FIRST:
            self._page -= 1
            self._setup_page()

    def _next_activated_cb(self, widget):
        self.next()

    def next(self):
        if self._page == self.PAGE_LAST:
            self.done()
        if self._current_page.props.valid:
            self._page += 1
            self._setup_page()

    def _done_activated_cb(self, widget):
        self.done()

    def done(self):
        name = self._name_page.get_name()
        color = self._color_page.get_color()

        self.emit('done', name, color)


class IntroWindow(gtk.Window):
    __gtype_name__ = 'SugarIntroWindow'

    def __init__(self):
        gtk.Window.__init__(self)

        self.props.decorated = False
        self.maximize()

        self._intro_box = _IntroBox()
        self._intro_box.connect('done', self._done_cb)

        self.add(self._intro_box)
        self._intro_box.show()
        self.connect('key-press-event', self.__key_press_cb)

    def _done_cb(self, box, name, color):
        self.hide()
        gobject.idle_add(self._create_profile_cb, name, color)

    def _create_profile_cb(self, name, color):
        create_profile(name, color)
        gtk.main_quit()

        return False

    def __key_press_cb(self, widget, event):
        if gtk.gdk.keyval_name(event.keyval) == 'Return':
            self._intro_box.next()
            return True
        elif gtk.gdk.keyval_name(event.keyval) == 'Escape':
            self._intro_box.back()
            return True
        return False


if __name__ == '__main__':
    w = IntroWindow()
    w.show()
    w.connect('destroy', gtk.main_quit)
    gtk.main()
