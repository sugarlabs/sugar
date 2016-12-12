# Copyright (C) 2007, Red Hat, Inc.
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
import os.path
import logging
from gettext import gettext as _
import pwd
import commands

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Gio
from gi.repository import GLib

from sugar3 import env
from sugar3 import profile
from sugar3.graphics import style
from sugar3.graphics.icon import Icon
from sugar3.graphics.xocolor import XoColor

from jarabe.intro import agepicker
from jarabe.intro import colorpicker
from jarabe.intro import genderpicker


def create_profile_with_nickname(nickname):
    user_profile = UserProfile()
    user_profile.nickname = nickname
    create_profile(user_profile)


def create_profile(user_profile):
    settings = Gio.Settings('org.sugarlabs.user')

    if user_profile.nickname in [None, '']:
        nick = settings.get_string('nick')
        if nick is not None:
            logging.debug('recovering old nickname %s' % (nick))
            user_profile.nickname = nick
    settings.set_string('nick', user_profile.nickname)

    colors = user_profile.colors
    if colors is None:
        colors = XoColor()
    settings.set_string('color', colors.to_string())

    genderpicker.save_gender(user_profile.gender)

    agepicker.save_age(user_profile.age)

    # DEPRECATED
    from gi.repository import GConf
    client = GConf.Client.get_default()

    client.set_string('/desktop/sugar/user/nick', user_profile.nickname)

    client.set_string('/desktop/sugar/user/color', colors.to_string())

    client.suggest_sync()

    if profile.get_pubkey() and profile.get_profile().privkey_hash:
        logging.info('Valid key pair found, skipping generation.')
        return

    # Generate keypair
    keypath = os.path.join(env.get_profile_path(), 'owner.key')
    if os.path.exists(keypath):
        os.rename(keypath, keypath + '.broken')
        logging.warning('Existing private key %s moved to %s.broken',
                        keypath, keypath)

    if os.path.exists(keypath + '.pub'):
        os.rename(keypath + '.pub', keypath + '.pub.broken')
        logging.warning('Existing public key %s.pub moved to %s.pub.broken',
                        keypath, keypath)

    logging.debug("Generating user keypair")

    cmd = "ssh-keygen -q -t dsa -f %s -C '' -N ''" % (keypath, )
    (s, o) = commands.getstatusoutput(cmd)
    if s != 0:
        logging.error('Could not generate key pair: %d %s', s, o)

    logging.debug("User keypair generated")


class _Page(Gtk.VBox):
    __gproperties__ = {
        'valid': (bool, None, None, False, GObject.PARAM_READABLE),
    }

    def __init__(self):
        Gtk.VBox.__init__(self)
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

        alignment = Gtk.Alignment.new(0.5, 0.5, 0, 0)
        self.pack_start(alignment, expand=True, fill=True, padding=0)

        grid = Gtk.Grid()
        grid.set_column_spacing(style.DEFAULT_SPACING)
        alignment.add(grid)

        label = Gtk.Label(label=_('Name:'))
        grid.attach(label, 0, 0, 1, 1)
        label.show()

        self._entry = Gtk.Entry()
        self._entry.connect('notify::text', self._text_changed_cb)
        self._entry.set_size_request(style.zoom(300), -1)
        self._entry.set_max_length(45)
        grid.attach(self._entry, 0, 1, 1, 1)
        self._entry.show()

        grid.show()
        alignment.show()

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

        alignment = Gtk.Alignment.new(0.5, 0.5, 0, 0)
        self.pack_start(alignment, expand=True, fill=True, padding=0)

        grid = Gtk.Grid()
        grid.set_column_spacing(style.DEFAULT_SPACING)
        alignment.add(grid)

        label = Gtk.Label(label=_('Click to change color:'))
        grid.attach(label, 0, 0, 1, 1)
        label.show()

        self._cp = colorpicker.ColorPicker()
        grid.attach(self._cp, 0, 1, 1, 1)
        self._cp.show()

        grid.show()
        alignment.show()

        self._color = self._cp.get_color()
        self.set_valid(True)

    def get_color(self):
        return self._cp.get_color()


class _GenderPage(_Page):

    def __init__(self):
        _Page.__init__(self)

        alignment = Gtk.Alignment.new(0.5, 0.5, 0, 0)
        self.pack_start(alignment, expand=True, fill=True, padding=0)

        grid = Gtk.Grid()
        grid.set_column_spacing(style.DEFAULT_SPACING)
        alignment.add(grid)

        label = Gtk.Label(label=_('Select gender:'))
        grid.attach(label, 0, 0, 1, 1)
        label.show()

        self._gp = genderpicker.GenderPicker()
        grid.attach(self._gp, 0, 1, 1, 1)
        self._gp.show()

        grid.show()
        alignment.show()

        self._gender = self._gp.get_gender()
        self.set_valid(True)

    def get_gender(self):
        return self._gp.get_gender()

    def update_color(self, color):
        self._gp.update_color(color)


class _AgePage(_Page):

    def __init__(self, gender):
        _Page.__init__(self)

        alignment = Gtk.Alignment.new(0.5, 0.5, 0, 0)
        self.pack_start(alignment, expand=True, fill=True, padding=0)

        grid = Gtk.Grid()
        grid.set_column_spacing(style.DEFAULT_SPACING)
        alignment.add(grid)

        self._ap = agepicker.AgePicker(gender, self)

        label = Gtk.Label(label=_(self._ap.get_label()))
        grid.attach(label, 0, 0, 1, 1)
        label.show()

        grid.attach(self._ap, 0, 1, 1, 1)
        self._ap.show()

        grid.show()
        alignment.show()

        self._age = self._ap.get_age()

    def update_gender(self, gender):
        self._ap.update_gender(gender)

    def update_color(self, color):
        self._ap.update_color(color)

    def get_age(self):
        return self._ap.get_age()


class _IntroBox(Gtk.VBox):
    done_signal = GObject.Signal('done', arg_types=([object]))

    PAGE_NAME = 0
    PAGE_COLOR = 1
    PAGE_GENDER = 2
    PAGE_AGE = 3

    PAGE_FIRST = min(PAGE_NAME, PAGE_COLOR, PAGE_GENDER, PAGE_AGE)
    PAGE_LAST = max(PAGE_NAME, PAGE_COLOR, PAGE_GENDER, PAGE_AGE)

    def __init__(self, start_on_age_page):
        Gtk.VBox.__init__(self)
        self.set_border_width(style.zoom(30))

        self._page = self.PAGE_NAME
        self._name_page = _NamePage(self)
        self._color_page = _ColorPage()
        self._gender_page = _GenderPage()
        self._age_page = _AgePage(None)
        self._current_page = None
        self._next_button = None

        settings = Gio.Settings('org.sugarlabs.user')
        default_nick = settings.get_string('default-nick')
        if default_nick != 'disabled':
            self._page = self.PAGE_COLOR
            if default_nick == 'system':
                pwd_entry = pwd.getpwuid(os.getuid())
                default_nick = (pwd_entry.pw_gecos.split(',')[0] or
                                pwd_entry.pw_name)
            self._name_page.set_name(default_nick)

        # XXX should also consider whether or not there is a nick
        nick = settings.get_string('nick')
        if start_on_age_page and nick:
            self._page = self.PAGE_AGE

        self._setup_page()

    def _setup_page(self):
        for child in self.get_children():
            self.remove(child)

        def _setup_name_page(self):
            self._current_page = self._name_page

        def _setup_color_page(self):
            self._current_page = self._color_page

        def _setup_gender_page(self):
            if self._color_page.get_color() is not None:
                self._gender_page.update_color(self._color_page.get_color())
            self._current_page = self._gender_page

        def _setup_age_page(self):
            if self._gender_page.get_gender() is not None:
                self._age_page.update_gender(self._gender_page.get_gender())
            if self._color_page.get_color() is not None:
                self._age_page.update_color(self._color_page.get_color())
            self._current_page = self._age_page

        setup_methods = {
            self.PAGE_NAME: _setup_name_page,
            self.PAGE_COLOR: _setup_color_page,
            self.PAGE_GENDER: _setup_gender_page,
            self.PAGE_AGE: _setup_age_page
        }

        setup_methods[self._page](self)
        self.pack_start(self._current_page, True, True, 0)
        self._current_page.show()

        button_box = Gtk.HButtonBox()
        if self._page == self.PAGE_FIRST:
            button_box.set_layout(Gtk.ButtonBoxStyle.END)
        else:
            button_box.set_layout(Gtk.ButtonBoxStyle.EDGE)
            back_button = Gtk.Button(_('Back'))
            image = Icon(icon_name='go-left')
            back_button.set_image(image)
            back_button.connect('clicked', self._back_activated_cb)
            button_box.pack_start(back_button, True, True, 0)
            back_button.show()

        self._next_button = Gtk.Button()
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
        button_box.pack_start(self._next_button, True, True, 0)
        self._next_button.show()

        self._current_page.connect('notify::valid',
                                   self._page_valid_changed_cb)

        self.pack_start(button_box, False, True, 0)
        button_box.show()

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
        if self._current_page.props.valid:
            if self._page == self.PAGE_LAST:
                self.done()
            else:
                self._page += 1
                self._setup_page()

    def _done_activated_cb(self, widget):
        self.done()

    def done(self):
        user_profile = UserProfile()
        user_profile.nickname = self._name_page.get_name()
        user_profile.colors = self._color_page.get_color()
        user_profile.gender = self._gender_page.get_gender()
        user_profile.age = self._age_page.get_age()

        self.done_signal.emit(user_profile)


class UserProfile():

    def __init__(self):
        self.nickname = None
        self.colors = None
        self.gender = None
        self.age = 0


class IntroWindow(Gtk.Window):
    __gtype_name__ = 'SugarIntroWindow'

    __gsignals__ = {
        'done': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, start_on_age_page=False):
        Gtk.Window.__init__(self)

        self.props.decorated = False
        self.maximize()

        self._intro_box = _IntroBox(start_on_age_page)
        self._intro_box.connect('done', self._done_cb)

        self.add(self._intro_box)
        self._intro_box.show()
        self.connect('key-press-event', self.__key_press_cb)

    def _done_cb(self, box, user_profile):
        self.hide()
        GLib.idle_add(self._create_profile_cb, user_profile)

    def _create_profile_cb(self, user_profile):
        create_profile(user_profile)
        self.emit("done")

        return False

    def __key_press_cb(self, widget, event):
        if Gdk.keyval_name(event.keyval) == 'Return':
            self._intro_box.next()
            return True
        elif Gdk.keyval_name(event.keyval) == 'Escape':
            self._intro_box.back()
            return True
        return False
if hasattr(IntroWindow, 'set_css_name'):
    IntroWindow.set_css_name('introwindow')


if __name__ == '__main__':
    w = IntroWindow()
    w.show()
    w.connect('destroy', Gtk.main_quit)
    Gtk.main()
