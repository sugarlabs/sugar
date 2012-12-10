# Copyright (C) 2006, Red Hat, Inc.
# Copyright (C) 2009, One Laptop Per Child Association Inc
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

from sugar3 import logger

logger.cleanup()
logger.start('shell')

import logging

logging.debug('%r STARTUP: Starting the shell')

import os
import sys
import subprocess
import shutil
import time

# Change the default encoding to avoid UnicodeDecodeError
# http://lists.sugarlabs.org/archive/sugar-devel/2012-August/038928.html
reload(sys)
sys.setdefaultencoding('utf-8')

import gettext

from gi.repository import GLib
from gi.repository import GConf
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Gst
import dbus.glib
from gi.repository import Wnck

from sugar3 import env

from jarabe.model.session import get_session_manager
from jarabe.model import screen
from jarabe.view import keyhandler
from jarabe.view import gesturehandler
from jarabe.view import cursortracker
from jarabe.journal import journalactivity
from jarabe.desktop import homewindow
from jarabe.model import notifications
from jarabe.model import filetransfer
from jarabe.view import launcher
from jarabe.model import keyboard
from jarabe.desktop import homewindow
from jarabe import config
from jarabe.model import sound
from jarabe import intro
from jarabe.intro.window import IntroWindow
from jarabe import frame
from jarabe.view.service import UIService

def unfreeze_dcon_cb():
    logging.debug('STARTUP: unfreeze_dcon_cb')
    screen.set_dcon_freeze(0)

def setup_frame_cb():
    logging.debug('STARTUP: setup_frame_cb')
    frame.get_view()

def setup_keyhandler_cb():
    logging.debug('STARTUP: setup_keyhandler_cb')
    keyhandler.setup(frame.get_view())

def setup_gesturehandler_cb():
    logging.debug('STARTUP: setup_gesturehandler_cb')
    gesturehandler.setup(frame.get_view())

def setup_cursortracker_cb():
    logging.debug('STARTUP: setup_cursortracker_cb')
    cursortracker.setup()

def setup_journal_cb():
    logging.debug('STARTUP: setup_journal_cb')
    journalactivity.start()

def show_software_updates_cb():
    logging.debug('STARTUP: show_software_updates_cb')
    if os.path.isfile(os.path.expanduser('~/.sugar-update')):
        home_window = homewindow.get_instance()
        home_window.get_home_box().show_software_updates_alert()

def setup_notification_service_cb():
    notifications.init()

def setup_file_transfer_cb():
    filetransfer.init()

def setup_window_manager():
    logging.debug('STARTUP: window_manager')

    # have to reset cursor(metacity sets it on startup)
    if subprocess.call('echo $DISPLAY; xsetroot -cursor_name left_ptr',
                       shell=True):
        logging.warning('Can not reset cursor')

    if subprocess.call('metacity-message disable-keybindings',
                       shell=True):
        logging.warning('Can not disable metacity keybindings')

    if subprocess.call('metacity-message disable-mouse-button-modifiers',
                       shell=True):
        logging.warning('Can not disable metacity mouse button modifiers')

def bootstrap():
    setup_window_manager()

    launcher.setup()

    GObject.idle_add(setup_frame_cb)
    GObject.idle_add(setup_keyhandler_cb)
    GObject.idle_add(setup_gesturehandler_cb)
    GObject.idle_add(setup_journal_cb)
    GObject.idle_add(setup_notification_service_cb)
    GObject.idle_add(setup_file_transfer_cb)
    GObject.idle_add(show_software_updates_cb)

    keyboard.setup()

def set_fonts():
    client = GConf.Client.get_default()
    face = client.get_string('/desktop/sugar/font/default_face')
    size = client.get_float('/desktop/sugar/font/default_size')
    settings = Gtk.Settings.get_default()
    settings.set_property("gtk-font-name", "%s %f" % (face, size))

def set_theme():
    settings = Gtk.Settings.get_default()
    sugar_theme = 'sugar-72'
    if 'SUGAR_SCALING' in os.environ:
        if os.environ['SUGAR_SCALING'] == '100':
            sugar_theme = 'sugar-100'
    settings.set_property('gtk-theme-name', sugar_theme)
    settings.set_property('gtk-icon-theme-name', 'sugar')

    icons_path = os.path.join(config.data_path, 'icons')
    Gtk.IconTheme.get_default().append_search_path(icons_path)

def start_home():
    ui_service = UIService()

    session_manager = get_session_manager()
    session_manager.start()

    # open homewindow before window_manager to let desktop appear fast
    home_window = homewindow.get_instance()
    home_window.show()

    screen = Wnck.Screen.get_default()
    screen.connect('window-manager-changed', __window_manager_changed_cb)
    _check_for_window_manager(screen)

def intro_window_done_cb(window):
    start_home()

def cleanup_temporary_files():
    try:
        # Remove temporary files. See http://bugs.sugarlabs.org/ticket/1876
        data_dir = os.path.join(env.get_profile_path(), 'data')
        shutil.rmtree(data_dir, ignore_errors=True)
        os.makedirs(data_dir)
    except OSError, e:
        # temporary files cleanup is not critical; it should not prevent
        # sugar from starting if (for example) the disk is full or read-only.
        print 'temporary files cleanup failed: %s' % e

def setup_locale():
    # NOTE: This needs to happen early because some modules register
    # translatable strings in the module scope.
    gettext.bindtextdomain('sugar', config.locale_path)
    gettext.bindtextdomain('sugar-toolkit', config.locale_path)
    gettext.textdomain('sugar')

    client = GConf.Client.get_default()
    timezone = client.get_string('/desktop/sugar/date/timezone')
    if timezone is not None and timezone:
        os.environ['TZ'] = timezone

def main():
    GLib.threads_init()
    Gdk.threads_init()
    dbus.glib.threads_init()
    Gst.init(sys.argv)

    cleanup_temporary_files()

    setup_locale()

    client = GConf.Client.get_default()
    client.set_string('/apps/metacity/general/mouse_button_modifier',
                      '<Super>')

    set_fonts()
    set_theme()

    # this must be added early, so that it executes and unfreezes the screen
    # even when we initially get blocked on the intro screen
    GObject.idle_add(unfreeze_dcon_cb)

    GObject.idle_add(setup_cursortracker_cb)
    # make sure we have the correct cursor in the intro screen
    # TODO #3204
    if subprocess.call('echo $DISPLAY; xsetroot -cursor_name left_ptr',
                       shell=True):
        logging.warning('Can not reset cursor')

    sound.restore()

    sys.path.append(config.ext_path)

    if not intro.check_profile():
        win = IntroWindow()
        win.connect("done", intro_window_done_cb)
        win.show_all()
    else:
        start_home()

    try:
        Gtk.main()
    except KeyboardInterrupt:
        print 'Ctrl+C pressed, exiting...'


def __window_manager_changed_cb(screen):
    _check_for_window_manager(screen)


def _check_for_window_manager(screen):
    wm_name = screen.get_window_manager_name()
    if wm_name is not None:
        screen.disconnect_by_func(__window_manager_changed_cb)
        bootstrap()


main()
