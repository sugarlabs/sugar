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

from sugar3 import logger

logger.cleanup()
logger.start('shell')

import logging

logging.debug('STARTUP: Starting the shell')

import os
import sys
import subprocess
import shutil

# Change the default encoding to avoid UnicodeDecodeError
# http://lists.sugarlabs.org/archive/sugar-devel/2012-August/038928.html
reload(sys)
sys.setdefaultencoding('utf-8')

# Disable overlay scrolling before GTK is loaded
os.environ['GTK_OVERLAY_SCROLLING'] = '0'
os.environ['LIBOVERLAY_SCROLLBAR'] = '0'

import gettext
from jarabe import config
# NOTE: This needs to happen early because some modules register
# translatable strings in the module scope.
gettext.bindtextdomain('sugar', config.locale_path)
gettext.bindtextdomain('sugar-toolkit-gtk3', config.locale_path)
gettext.textdomain('sugar')

# publish sugar version in the environment
os.environ['SUGAR_VERSION'] = config.version

from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)

# define the versions of used libraries that are required
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
gi.require_version('Wnck', '3.0')
gi.require_version('SugarExt', '1.0')
gi.require_version('GdkX11', '3.0')
gi.require_version('GConf', '2.0')

from gi.repository import GObject
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gst
from gi.repository import Wnck

from sugar3 import env

from jarabe.model.session import get_session_manager
from jarabe.model.update import updater
from jarabe.model import screen
from jarabe.view import keyhandler
from jarabe.view import gesturehandler
from jarabe.view import cursortracker
from jarabe.journal import journalactivity
from jarabe.model import notifications
from jarabe.model import filetransfer
from jarabe.view import launcher
from jarabe.model import keyboard
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


_metacity_process = None
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


def setup_window_manager():
    logging.debug('STARTUP: window_manager')

    if subprocess.call('metacity-message disable-keybindings',
                       shell=True):
        logging.warning('Can not disable metacity keybindings')

    if subprocess.call('metacity-message disable-mouse-button-modifiers',
                       shell=True):
        logging.warning('Can not disable metacity mouse button modifiers')


def __window_manager_changed_cb(screen):
    _check_for_window_manager(screen)


def _complete_desktop_startup():
    launcher.setup()

    GLib.idle_add(setup_frame_cb)
    GLib.idle_add(setup_keyhandler_cb)
    GLib.idle_add(setup_gesturehandler_cb)
    GLib.idle_add(setup_journal_cb)
    GLib.idle_add(setup_notification_service_cb)
    GLib.idle_add(setup_file_transfer_cb)
    GLib.timeout_add_seconds(600, updater.startup_periodic_update)

    apisocket.start()

    testrunner.check_environment()


def _check_for_window_manager(screen):
    wm_name = screen.get_window_manager_name()
    if wm_name is None:
        return

    screen.disconnect_by_func(__window_manager_changed_cb)

    setup_window_manager()

    global _window_manager_started
    _window_manager_started = True

    global _starting_desktop
    if _starting_desktop:
        _complete_desktop_startup()


def __window_manager_failed_cb(fd, condition):
    logging.error('window manager did fail, restarting')
    GObject.source_remove(_metacity_sid)
    GObject.timeout_add(1000, _restart_window_manager)
    return False


def _restart_window_manager():
    global _metacity_process, _metacity_sid

    _metacity_process = subprocess.Popen(
        ['metacity', '--no-force-fullscreen', '--no-composite'],
        stdout=subprocess.PIPE)
    _metacity_sid = GObject.io_add_watch(_metacity_process.stdout, GLib.IO_HUP,
                                         __window_manager_failed_cb)
    return False


def _start_window_manager():
    settings = Gio.Settings.new('org.gnome.desktop.interface')
    settings.set_string('cursor-theme', 'sugar')

    _restart_window_manager()

    screen = Wnck.Screen.get_default()
    screen.connect('window-manager-changed', __window_manager_changed_cb)

    _check_for_window_manager(screen)


def _stop_window_manager():
    _metacity_process.terminate()


def _begin_desktop_startup():
    global _starting_desktop
    _starting_desktop = True

    UIService()

    session_manager = get_session_manager()
    session_manager.start()

    # open homewindow before window_manager to let desktop appear fast
    home_window = homewindow.get_instance()
    home_window.show()


def __intro_window_done_cb(window):
    _begin_desktop_startup()

    global _window_manager_started
    if _window_manager_started:
        _complete_desktop_startup()


def cleanup_temporary_files():
    try:
        # Remove temporary files. See http://bugs.sugarlabs.org/ticket/1876
        data_dir = os.path.join(env.get_profile_path(), 'data')
        shutil.rmtree(data_dir, ignore_errors=True)
        os.makedirs(data_dir)
    except OSError as e:
        # temporary files cleanup is not critical; it should not prevent
        # sugar from starting if (for example) the disk is full or read-only.
        print 'temporary files cleanup failed: %s' % e


def _migrate_journal_mimeregistry():
    from gi.repository import GConf
    client = GConf.Client.get_default()

    # Now this isn't good
    # keys in /desktop/sugar/journal/defaults are mime types
    # which are of the sort text/plain
    # so, GConf is thinking test is a directory and the key is plain
    # while the key should be 'text/plain'

    gconf_defaults_dir = '/desktop/sugar/journal/defaults'

    entries = client.all_entries(gconf_defaults_dir)
    for directory in client.all_dirs(gconf_defaults_dir):
        entries.extend(client.all_entries(directory))

    prefix = gconf_defaults_dir + '/'
    prefix_length = len(prefix)

    gconf_defaults = {}
    for entry in entries:
        key = entry.get_key()
        key = key[prefix_length:]

        # entry.get_value().get_string() causes sugar to crash later
        # not on the call, but after some random time
        # was impossible to debug (almost impossible)
        value = entry.value.get_string()
        gconf_defaults[key] = value

    variant = GLib.Variant('a{ss}', gconf_defaults)

    settings = Gio.Settings('org.sugarlabs.journal')
    settings.set_value('mime-registry', variant)


def _migrate_homeviews_settings():
    from gi.repository import GConf
    client = GConf.Client.get_default()

    # Merge several keys into one... yay!
    options = client.get('/desktop/sugar/desktop/view-icons')
    gconf_view_icons = []
    if options:
        gconf_view_icons = [gval.get_string() for gval in options.get_list()]

    # assume view-icons is the leading key
    number_of_views = len(gconf_view_icons)

    layouts = []
    prefix = '/desktop/sugar/desktop/favorites_layout'

    entries = client.all_entries('/desktop/sugar/desktop')
    for entry in entries:
        key = entry.get_key()
        if key.startswith(prefix):
            # entry.get_value().get_string() causes sugar to crash later
            # not on the call, but after some random time
            # was impossible to debug (almost impossible)
            value = entry.value.get_string()
            layouts.append((key, value))

    layouts.sort()
    gconf_layouts = [layout[1] for layout in layouts][:number_of_views]

    while len(gconf_layouts) < number_of_views:
        gconf_layouts.append('ring-layout')

    options = client.get('/desktop/sugar/desktop/favorite-icons')
    gconf_fav_icons = []
    if options:
        gconf_fav_icons = [gval.get_string() for gval in options.get_list()]
        gconf_fav_icons = gconf_fav_icons[:number_of_views]

    while len(gconf_fav_icons) < number_of_views:
        gconf_fav_icons.append('emblem-favorite')

    homeviews = []
    for i, view_icon in enumerate(gconf_view_icons):
        homeviews.append({'view-icon': view_icon, 'layout': gconf_layouts[i],
                          'favorite-icon': gconf_fav_icons[i]})

    variant = GLib.Variant('aa{ss}', homeviews)
    settings = Gio.Settings('org.sugarlabs.desktop')
    settings.set_value('homeviews', variant)


def _migrate_gconf_to_gsettings():
    try:
        subprocess.call('gsettings-data-convert')
    except subprocess.CalledProcessError:
        logging.error('Unable to convert data.')

    settings = Gio.Settings('org.sugarlabs')
    migrated = settings.get_boolean('gsettings-migrated')

    if not migrated:
        _migrate_journal_mimeregistry()
        _migrate_homeviews_settings()

        settings.set_boolean('gsettings-migrated', True)


def setup_timezone():
    settings = Gio.Settings('org.sugarlabs.date')
    timezone = settings.get_string('timezone')
    if timezone is not None and timezone:
        os.environ['TZ'] = timezone


def setup_fonts():
    settings = Gio.Settings('org.sugarlabs.font')
    face = settings.get_string('default-face')
    size = settings.get_double('default-size')

    settings = Gtk.Settings.get_default()
    settings.set_property("gtk-font-name", "%s %f" % (face, size))


def setup_proxy():
    protos = ['http', 'https', 'ftp', 'socks']
    env_variables = ['{}_proxy'.format(proto) for proto in protos]
    schemas = ['org.sugarlabs.system.proxy.{}'.format(
        proto) for proto in protos]

    g_mode = Gio.Settings('org.sugarlabs.system.proxy').get_string('mode')
    if g_mode == 'manual':
        counter = 0
        for schema in schemas:
            setting_schema = Gio.Settings(schema)

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
        os.environ['no_proxy'] = ",".join(Gio.Settings(
            'org.sugarlabs.system.proxy').get_strv('ignore-hosts'))

    elif g_mode == 'none':
        for each_env_variable in env_variables:
            os.environ[each_env_variable] = ''


def setup_theme():
    settings = Gtk.Settings.get_default()
    sugar_theme = 'sugar-72'
    if 'SUGAR_SCALING' in os.environ:
        if os.environ['SUGAR_SCALING'] == '100':
            sugar_theme = 'sugar-100'
    settings.set_property('gtk-theme-name', sugar_theme)
    settings.set_property('gtk-icon-theme-name', 'sugar')
    settings.set_property('gtk-cursor-blink-timeout', 3)
    settings.set_property('gtk-button-images', True)

    icons_path = os.path.join(config.data_path, 'icons')
    Gtk.IconTheme.get_default().append_search_path(icons_path)


def _start_intro(start_on_age_page=False):
    window = IntroWindow(start_on_age_page=start_on_age_page)
    window.connect('done', __intro_window_done_cb)
    window.show()


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


def main():
    # This can be removed once pygobject-3.10 is a requirement.
    # https://bugzilla.gnome.org/show_bug.cgi?id=686914
    GLib.threads_init()

    Gst.init(sys.argv)

    _migrate_gconf_to_gsettings()

    cleanup_temporary_files()

    _start_window_manager()

    setup_timezone()
    setup_fonts()
    setup_theme()
    setup_proxy()

    # this must be added early, so that it executes and unfreezes the screen
    # even when we initially get blocked on the intro screen
    GLib.idle_add(unfreeze_screen_cb)

    GLib.idle_add(setup_cursortracker_cb)
    sound.restore()
    keyboard.setup()
    brightness.get_instance()

    sys.path.append(config.ext_path)

    if not _check_profile():
        _start_intro()
    elif not _check_group_label():
        _start_intro(start_on_age_page=True)
    else:
        _begin_desktop_startup()

    try:
        Gtk.main()
    except KeyboardInterrupt:
        print 'Ctrl+C pressed, exiting...'

    _stop_window_manager()

main()
