# Copyright (C) 2006, Red Hat, Inc.
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
import gettext

# HACK we need to import numpy before gtk otherwise we traceback in
# some locales. See http://dev.laptop.org/ticket/5559.
import numpy

import pygtk
pygtk.require('2.0')
import gtk
import gobject

from sugar import env
from sugar import logger
from sugar.profile import get_profile

import view.Shell
from shellservice import ShellService
from hardware import hardwaremanager
from intro import intro
from session import get_session_manager
import logsmanager
import config

def _start_matchbox():
    cmd = ['matchbox-window-manager']

    cmd.extend(['-use_titlebar', 'no'])
    cmd.extend(['-theme', 'sugar'])
    cmd.extend(['-kbdconfig', os.path.join(config.data_path, 'kbdconfig')])

    gobject.spawn_async(cmd, flags=gobject.SPAWN_SEARCH_PATH)

def _save_session_info():
    # Save our DBus Session Bus address somewhere it can be found
    #
    # WARNING!!! this is going away at some near future point, 
    #            do not rely on it
    #
    session_info_file = os.path.join(env.get_profile_path(), "session.info")
    f = open(session_info_file, "w")

    cp = ConfigParser()
    cp.add_section('Session')
    cp.set('Session', 'dbus_address', os.environ['DBUS_SESSION_BUS_ADDRESS'])
    cp.set('Session', 'display', gtk.gdk.display_get_default().get_name())
    cp.write(f)

    f.close()

def _setup_translations():
    locale_path = os.path.join(config.prefix, 'share', 'locale')
    domain = 'sugar'

    gettext.bindtextdomain(domain, locale_path)
    gettext.textdomain(domain)

def check_cm(bus_name):
    try:
        import dbus
        bus = dbus.SessionBus()
        bus_object = bus.get_object('org.freedesktop.DBus', 
                                    '/org/freedesktop/DBus')
        name_ = bus_object.GetNameOwner(bus_name, 
                                        dbus_interface='org.freedesktop.DBus')
    except dbus.DBusException:
        return False
    return True

def _shell_started_cb():
    # Unfreeze the display
    hw_manager = hardwaremanager.get_manager()
    hw_manager.set_dcon_freeze(0)

def main():
    gobject.idle_add(_shell_started_cb)

    logsmanager.setup()
    logger.start('shell')

    _save_session_info()
    _start_matchbox()
    _setup_translations()

    hw_manager = hardwaremanager.get_manager()
    hw_manager.startup()

    icons_path = os.path.join(config.data_path, 'icons')
    gtk.icon_theme_get_default().append_search_path(icons_path)

    # Do initial setup if needed
    if not get_profile().is_valid():
        win = intro.IntroWindow()
        win.show_all()
        gtk.main()

    # set timezone    
    if os.environ.has_key('TZ'):    
        os.environ['TZ'] = get_profile().timezone

    if os.environ.has_key("SUGAR_TP_DEBUG"):
        # Allow the user time to start up telepathy connection managers
        # using the Sugar DBus bus address
        import time
        from telepathy.client import ManagerRegistry

        registry = ManagerRegistry()
        registry.LoadManagers()

        debug_flags = os.environ["SUGAR_TP_DEBUG"].split(',')
        for cm_name in debug_flags:
            if cm_name not in ["gabble", "salut"]:
                continue

            try:
                cm = registry.services[cm_name]
            except KeyError:
                print RuntimeError("%s connection manager not found!" % cm_name)

            while not check_cm(cm['busname']):
                print "Waiting for %s on: DBUS_SESSION_BUS_ADDRESS=%s" % \
                    (cm_name, os.environ["DBUS_SESSION_BUS_ADDRESS"])
                try:
                    time.sleep(5)
                except KeyboardInterrupt:
                    print "Got Ctrl+C, continuing..."
                    break

    # TODO: move initializations from the Shell constructor to a start() method
    view.Shell.get_instance()
    ShellService()

    session_manager = get_session_manager()
    session_manager.start()

    try:
        gtk.main()
    except KeyboardInterrupt:
        print 'Ctrl+C pressed, exiting...'

    session_info_file = os.path.join(env.get_profile_path(), "session.info")
    os.remove(session_info_file)

