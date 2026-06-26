# Copyright (C) 2006-2008 Red Hat, Inc.
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
import logging

import dbus

_logger = logging.getLogger('screen')


_HARDWARE_MANAGER_INTERFACE = 'org.freedesktop.ohm.Keystore'
_HARDWARE_MANAGER_SERVICE = 'org.freedesktop.ohm'
_HARDWARE_MANAGER_OBJECT_PATH = '/org/freedesktop/ohm/Keystore'

POWERD_FLAG_DIR = '/etc/powerd/flags'


_SCREENSAVER_SERVICE = 'org.freedesktop.ScreenSaver'
_SCREENSAVER_PATH = '/org/freedesktop/ScreenSaver'
_SCREENSAVER_INTERFACE = 'org.freedesktop.ScreenSaver'

_inhibit_cookie = None


def using_powerd():
    """Returns True only on genuine OLPC hardware with powerd running.
    
    On all modern systems (Ubuntu, Fedora, Debian with GNOME/KDE/Wayland),
    this returns False and idle management is handled by the compositor
    via org.freedesktop.ScreenSaver D-Bus inhibit instead.
    """
    return os.access(POWERD_FLAG_DIR, os.W_OK)


def _get_ohm():
    """Get OHM (Open Hardware Manager) DBus proxy - OLPC XO hardware only."""
    bus = dbus.SystemBus()
    proxy = bus.get_object(_HARDWARE_MANAGER_SERVICE,
                           _HARDWARE_MANAGER_OBJECT_PATH,
                           follow_name_owner_changes=True)
    return dbus.Interface(proxy, _HARDWARE_MANAGER_INTERFACE)


def unfreeze():
    """Unfreeze the display.
    
    GTK3/OLPC: Called once at startup to wake the OLPC DCON display chip 
    after it was frozen by ohmd/powerd during boot.
    
    GTK4/Wayland: On OLPC hardware, still calls ohmd. On all other systems
    (Ubuntu, Fedora, Debian), instead registers a ScreenSaver idle inhibitor
    which prevents the compositor from blanking/suspending while Sugar is active.
    This uses org.freedesktop.ScreenSaver which is supported by:
      - GNOME (routes to zwp_idle_inhibit_unstable_v1 on Wayland)
      - KDE Plasma
      - XFCE (via xfce4-screensaver or xss-lock)
      - Any XDG-portal-supporting compositor
    """
    if using_powerd():

        try:
            _get_ohm().SetKey('display.dcon_freeze', 0)
            _logger.debug('OLPC display unfrozen via ohmd')
        except dbus.DBusException as e:
            _logger.warning('Failed to unfreeze OLPC display: %s', e)
        return


    _inhibit_screensaver()


def _inhibit_screensaver():
    """Register an idle inhibitor via org.freedesktop.ScreenSaver D-Bus.
    
    This prevents screensaver/sleep while Sugar is the active desktop.
    The inhibitor is automatically released when Sugar exits.
    
    Supported by: Ubuntu, Fedora, Debian+GNOME, KDE, XFCE, LXQt.
    On Wayland compositors, xdg-desktop-portal routes this to the native
    zwp_idle_inhibit_unstable_v1 Wayland protocol.
    """
    global _inhibit_cookie
    if _inhibit_cookie is not None:

        return

    try:
        bus = dbus.SessionBus()
        proxy = bus.get_object(_SCREENSAVER_SERVICE, _SCREENSAVER_PATH)
        screensaver = dbus.Interface(proxy, _SCREENSAVER_INTERFACE)

        _inhibit_cookie = screensaver.Inhibit(
            'org.sugarlabs.Shell',
            'Sugar is the active desktop session'
        )
        _logger.debug('Idle inhibitor registered, cookie=%s', _inhibit_cookie)
    except dbus.DBusException as e:

        _logger.info('Could not register idle inhibitor (no screensaver daemon): %s', e)


def release_inhibitor():
    """Release the idle inhibitor when Sugar is shutting down.
    
    Call this in Sugar's shutdown sequence so the inhibitor is cleanly
    released instead of timing out. Matched with unfreeze() in startup.
    """
    global _inhibit_cookie
    if _inhibit_cookie is None:
        return

    try:
        bus = dbus.SessionBus()
        proxy = bus.get_object(_SCREENSAVER_SERVICE, _SCREENSAVER_PATH)
        screensaver = dbus.Interface(proxy, _SCREENSAVER_INTERFACE)
        screensaver.UnInhibit(_inhibit_cookie)
        _logger.debug('Idle inhibitor released')
    except dbus.DBusException as e:
        _logger.warning('Failed to release idle inhibitor: %s', e)
    finally:
        _inhibit_cookie = None
