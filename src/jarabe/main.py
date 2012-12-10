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

import os
import sys
import time
import subprocess
import shutil

# Change the default encoding to avoid UnicodeDecodeError
# http://lists.sugarlabs.org/archive/sugar-devel/2012-August/038928.html
reload(sys)
sys.setdefaultencoding('utf-8')

if os.environ.get('SUGAR_LOGGER_LEVEL', '') == 'debug':
    print '%r STARTUP: Starting the shell' % time.time()
    sys.stdout.flush()

import gettext
import logging
import sys

from gi.repository import GLib
from gi.repository import GConf
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Gst
import dbus.glib
from gi.repository import Wnck

def start_ui_service():
    from jarabe.view.service import UIService

    ui_service = UIService()

def start_session_manager():
    from jarabe.model.session import get_session_manager

    session_manager = get_session_manager()
    session_manager.start()

def unfreeze_dcon_cb():
    logging.debug('STARTUP: unfreeze_dcon_cb')
    from jarabe.model import screen

    screen.set_dcon_freeze(0)

def setup_frame_cb():
    logging.debug('STARTUP: setup_frame_cb')
    from jarabe import frame
    frame.get_view()

def setup_keyhandler_cb():
    logging.debug('STARTUP: setup_keyhandler_cb')
    from jarabe.view import keyhandler
    from jarabe import frame
    keyhandler.setup(frame.get_view())

def setup_gesturehandler_cb():
    logging.debug('STARTUP: setup_gesturehandler_cb')
    from jarabe.view import gesturehandler
    from jarabe import frame
    gesturehandler.setup(frame.get_view())

def setup_cursortracker_cb():
    logging.debug('STARTUP: setup_cursortracker_cb')
    from jarabe.view import cursortracker
    cursortracker.setup()

def setup_journal_cb():
    logging.debug('STARTUP: setup_journal_cb')
    from jarabe.journal import journalactivity
    journalactivity.start()

def show_software_updates_cb():
    logging.debug('STARTUP: show_software_updates_cb')
    if os.path.isfile(os.path.expanduser('~/.sugar-update')):
        from jarabe.desktop import homewindow
        home_window = homewindow.get_instance()
        home_window.get_home_box().show_software_updates_alert()

def setup_notification_service_cb():
    from jarabe.model import notifications
    notifications.init()

def setup_file_transfer_cb():
    from jarabe.model import filetransfer
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

    from jarabe.view import launcher
    launcher.setup()

    GObject.idle_add(setup_frame_cb)
    GObject.idle_add(setup_keyhandler_cb)
    GObject.idle_add(setup_gesturehandler_cb)
    GObject.idle_add(setup_journal_cb)
    GObject.idle_add(setup_notification_service_cb)
    GObject.idle_add(setup_file_transfer_cb)
    GObject.idle_add(show_software_updates_cb)

    from jarabe.model import keyboard
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

def start_home():
    from jarabe.desktop import homewindow

    start_ui_service()
    start_session_manager()

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
        from sugar3 import env
        # Remove temporary files. See http://bugs.sugarlabs.org/ticket/1876
        data_dir = os.path.join(env.get_profile_path(), 'data')
        shutil.rmtree(data_dir, ignore_errors=True)
        os.makedirs(data_dir)
    except OSError, e:
        # temporary files cleanup is not critical; it should not prevent
        # sugar from starting if (for example) the disk is full or read-only.
        print 'temporary files cleanup failed: %s' % e

def main():
    GLib.threads_init()
    Gdk.threads_init()
    dbus.glib.threads_init()
    Gst.init(sys.argv)

    cleanup_temporary_files()

    from sugar3 import logger
    # NOTE: This needs to happen so early because some modules register
    # translatable strings in the module scope.
    from jarabe import config
    gettext.bindtextdomain('sugar', config.locale_path)
    gettext.bindtextdomain('sugar-toolkit', config.locale_path)
    gettext.textdomain('sugar')

    from jarabe.model import sound
    from jarabe import intro
    from jarabe.intro.window import IntroWindow

    logger.cleanup()
    logger.start('shell')

    client = GConf.Client.get_default()
    client.set_string('/apps/metacity/general/mouse_button_modifier',
                      '<Super>')

    timezone = client.get_string('/desktop/sugar/date/timezone')
    if timezone is not None and timezone:
        os.environ['TZ'] = timezone

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

    icons_path = os.path.join(config.data_path, 'icons')
    Gtk.IconTheme.get_default().append_search_path(icons_path)

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
