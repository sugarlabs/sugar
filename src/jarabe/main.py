# Copyright (C) 2006, Red Hat, Inc.
# Copyright (C) 2009, One Laptop Per Child Association Inc
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

from sugar4 import logger

#logger.cleanup()
#logger.start('shell')

import logging

logging.debug('STARTUP: Starting the shell')

import os
import sys
import shutil

# Disable overlay scrolling before GTK is loaded
os.environ['GTK_OVERLAY_SCROLLING'] = '0'
os.environ['LIBOVERLAY_SCROLLBAR'] = '0'

import gettext
from jarabe import config
# must happen early; some modules register translatable strings at import time
gettext.bindtextdomain('sugar', config.locale_path)
gettext.bindtextdomain('sugar-toolkit-gtk4', config.locale_path)
gettext.textdomain('sugar')

os.environ['SUGAR_VERSION'] = config.version

from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)

import gi
gi.require_version('Gtk', '4.0')
try:
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst
    HAS_GST = True
except ValueError:
    HAS_GST = False
    logging.warning("Gst 1.0 not available. Running without GStreamer.")

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from sugar4 import env

from jarabe.model.session import get_session_manager
from jarabe.model.update import updater
from jarabe.model import screen
from jarabe.model import shell
from jarabe.view import keyhandler
from jarabe.view import gesturehandler
from jarabe.view import cursortracker
from jarabe.journal import journalactivity
from jarabe.model import notifications
from jarabe.model import filetransfer
from jarabe.view import launcher
#from jarabe.model import keyboard
from jarabe.desktop import homewindow
from jarabe.model.sound import sound
from jarabe import intro
from jarabe.intro.window import IntroWindow
from jarabe.intro.window import create_profile_with_nickname
from jarabe import frame
from jarabe.view.service import UIService
from jarabe import apisocket
from jarabe import testrunner
from jarabe.model import brightness

_window_manager_started = False
_starting_desktop = False


def unfreeze_screen_cb():
    logging.debug('STARTUP: unfreeze_screen_cb')
    screen.unfreeze()


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


def setup_notification_service_cb():
    notifications.init()


def setup_file_transfer_cb():
    filetransfer.init()


def _complete_desktop_startup():
    launcher.setup()

    setup_frame_cb()
    GLib.idle_add(setup_gesturehandler_cb)
    GLib.idle_add(setup_journal_cb)
    GLib.idle_add(setup_notification_service_cb)
    GLib.idle_add(setup_file_transfer_cb)
    GLib.timeout_add_seconds(600, updater.startup_periodic_update)

    apisocket.start()

    testrunner.check_environment()


def _start_window_manager():
    global _cursor_theme_settings, _cursor_theme

    _cursor_theme_settings = Gio.Settings.new('org.gnome.desktop.interface')
    _cursor_theme = _cursor_theme_settings.get_string('cursor-theme')

    global _starting_desktop
    if _starting_desktop:
        _complete_desktop_startup()


def _begin_desktop_startup():
    from jarabe.model import shell as shell_model
    global _starting_desktop
    _starting_desktop = True

    UIService()

    shell_instance = shell_model.get_model()
    _setup_main_window(shell_instance)

    home_window = homewindow.get_instance()

    setup_keyhandler_cb()

    shell_instance.stack.add_named(home_window, "home")
    shell_instance.stack.add_named(shell_instance.compositor, "activity")
    shell_instance.stack.set_visible_child_name("home")

    os.environ["WAYLAND_DISPLAY"] = "wayland-sugar"
    if "DISPLAY" in os.environ:
        del os.environ["DISPLAY"]

    session_manager = get_session_manager()

    _complete_desktop_startup()

    # Clear the startup 'wait' cursor now that the desktop is ready.
    # busy() was called in HomeWindow.__init__; unbusy() matches it.
    GLib.idle_add(home_window.unbusy)


def __intro_window_done_cb(window):
    _begin_desktop_startup()

    global _window_manager_started
    if _window_manager_started:
        _complete_desktop_startup()


def cleanup_temporary_files():
    try:
        # see http://bugs.sugarlabs.org/ticket/1876
        data_dir = os.path.join(env.get_profile_path(), 'data')
        shutil.rmtree(data_dir, ignore_errors=True)
        os.makedirs(data_dir)
    except OSError as e:
        # non-fatal: full or read-only disk should not block startup
        logging.warning('temporary files cleanup failed: %s', e)


def setup_timezone():
    settings = Gio.Settings.new('org.sugarlabs.date')
    timezone = settings.get_string('timezone')
    if timezone is not None and timezone:
        os.environ['TZ'] = timezone


def setup_fonts():
    settings = Gio.Settings.new('org.sugarlabs.font')
    face = settings.get_string('default-face')
    size = settings.get_double('default-size')

    gtk_settings = Gtk.Settings.get_default()
    gtk_settings.set_property('gtk-font-name', '%s %f' % (face, size))


def setup_proxy():
    protos = ['http', 'https', 'ftp', 'socks']
    env_variables = ['{}_proxy'.format(proto) for proto in protos]
    schemas = ['org.sugarlabs.system.proxy.{}'.format(
        proto) for proto in protos]

    g_mode = Gio.Settings.new('org.sugarlabs.system.proxy').get_string('mode')
    if g_mode == 'manual':
        counter = 0
        for schema in schemas:
            setting_schema = Gio.Settings.new(schema)

            if ((env_variables[counter] == 'http_proxy') and
                    setting_schema.get_boolean('use-authentication')):
                text_to_set = "%s://%s:%s@%s:%s/" % (
                    protos[counter],
                    setting_schema.get_string('authentication-user'),
                    setting_schema.get_string('authentication-password'),
                    setting_schema.get_string('host'),
                    str(setting_schema.get_int('port')))
            else:
                text_to_set = "%s://%s:%s/" % (
                    protos[counter],
                    setting_schema.get_string('host'),
                    str(setting_schema.get_int('port')))

            os.environ[env_variables[counter]] = text_to_set
            os.environ[env_variables[counter].upper()] = text_to_set
            counter += 1
        os.environ['no_proxy'] = ",".join(Gio.Settings.new(
            'org.sugarlabs.system.proxy').get_strv('ignore-hosts'))

    elif g_mode == 'none':
        for each_env_variable in env_variables:
            if each_env_variable in os.environ:
                del os.environ[each_env_variable]


def setup_theme():
    from gi.repository import Gdk
    gtk_settings = Gtk.Settings.get_default()
    sugar_theme = 'sugar-72'
    if 'SUGAR_SCALING' in os.environ:
        if os.environ['SUGAR_SCALING'] == '100':
            sugar_theme = 'sugar-100'
    gtk_settings.set_property('gtk-theme-name', sugar_theme)
    gtk_settings.set_property('gtk-icon-theme-name', 'sugar')
    gtk_settings.set_property('gtk-cursor-blink-timeout', 3)
    gtk_settings.set_property('gtk-overlay-scrolling', False)

    icons_path = os.path.join(config.data_path, 'icons')
    Gtk.IconTheme.get_for_display(
        Gdk.Display.get_default()).add_search_path(icons_path)


def _setup_main_window(shell_instance):
    if not shell_instance._main_window:
        shell_instance._main_window = Gtk.ApplicationWindow(application=shell_instance)
        shell_instance._main_window.set_title("Sugar")
        
        shell_instance._overlay = Gtk.Overlay()
        shell_instance._overlay.set_child(shell_instance.stack)
        
        shell_instance._main_window.set_child(shell_instance._overlay)
        if os.environ.get('SUGAR_WINDOWED', '0') == '1':
            shell_instance._main_window.set_default_size(1024, 768)
        else:
            shell_instance._main_window.fullscreen()
        shell_instance._main_window.present()


def _start_intro(shell, start_on_age_page=False):
    _setup_main_window(shell)
    intro_box = IntroWindow(start_on_age_page=start_on_age_page)

    shell.stack.add_named(intro_box, "intro")
    shell.stack.set_visible_child_name("intro")
    intro_box.connect('done', __intro_window_done_cb)


def _check_profile():
    if intro.check_profile():
        return True

    profile_name = os.environ.get("SUGAR_PROFILE_NAME", None)
    if profile_name is not None:
        create_profile_with_nickname(profile_name)
        return True

    return False


def _check_group_label():
    return intro.check_group_label()


def main(shell):
    logging.warning("Running main")
    
    # Create default profile directories if they do not exist
    profile_path = env.get_profile_path()
    for subdir in ['datastore', 'logs', 'data']:
        path = os.path.join(profile_path, subdir)
        if not os.path.exists(path):
            try:
                os.makedirs(path, 0o770)
            except OSError as e:
                logging.error('Failed to create directory %s: %s', path, e)

    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    if HAS_GST:
        Gst.init(sys.argv)

    cleanup_temporary_files()

    _start_window_manager()

    setup_timezone()
    setup_fonts()
    setup_theme()
    setup_proxy()

    # must run early so the screen unfreezes even if blocked on intro
    GLib.idle_add(unfreeze_screen_cb)

    GLib.idle_add(setup_cursortracker_cb)
    sound.restore()
    brightness.get_instance()

    sys.path.append(config.ext_path)

    if not _check_profile():
        _start_intro(shell)
    elif not _check_group_label():
        _start_intro(shell, start_on_age_page=True)
    else:
        _begin_desktop_startup()

shell = shell.get_model()

from sugar4.activity import activityfactory
def _get_compositor_fd():
    if shell.compositor is not None:
        return shell.compositor.get_client_socket_fd()
    return -1
activityfactory.set_compositor_fd_getter(_get_compositor_fd)

shell.connect('activate', main)
shell.run(None)
