# Copyright (C) 2008, Red Hat, Inc.
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

from gi.repository import Gtk
import dbus
import os
import logging

from sugar3 import session


_session_manager = None


def have_systemd():
    return os.access("/run/systemd/seats", 0) >= 0


class SessionManager(session.SessionManager):
    MODE_LOGOUT = 0
    MODE_SHUTDOWN = 1
    MODE_REBOOT = 2

    def __init__(self):
        session.SessionManager.__init__(self)
        self._logout_mode = None

    def logout(self):
        self._logout_mode = self.MODE_LOGOUT
        self.initiate_shutdown()

    def shutdown(self):
        self._logout_mode = self.MODE_SHUTDOWN
        self.initiate_shutdown()

    def reboot(self):
        self._logout_mode = self.MODE_REBOOT
        self.initiate_shutdown()

    def shutdown_completed(self):
        if self._logout_mode != self.MODE_LOGOUT:
            bus = dbus.SystemBus()
            if have_systemd():
                try:
                    proxy = bus.get_object('org.freedesktop.login1',
                                           '/org/freedesktop/login1')
                    pm = dbus.Interface(proxy,
                                        'org.freedesktop.login1.Manager')

                    if self._logout_mode == self.MODE_SHUTDOWN:
                        pm.PowerOff(False)
                    elif self._logout_mode == self.MODE_REBOOT:
                        pm.Reboot(True)
                except:
                    logging.exception('Can not stop sugar')
                    self.session.cancel_shutdown()
                    return
            else:
                CONSOLEKIT_DBUS_PATH = '/org/freedesktop/ConsoleKit/Manager'
                try:
                    proxy = bus.get_object('org.freedesktop.ConsoleKit',
                                           CONSOLEKIT_DBUS_PATH)
                    pm = dbus.Interface(proxy,
                                        'org.freedesktop.ConsoleKit.Manager')

                    if self._logout_mode == self.MODE_SHUTDOWN:
                        pm.Stop()
                    elif self._logout_mode == self.MODE_REBOOT:
                        pm.Restart()
                except:
                    logging.exception('Can not stop sugar')
                    self.session.cancel_shutdown()
                    return

        session.SessionManager.shutdown_completed(self)
        Gtk.main_quit()


def get_session_manager():
    global _session_manager

    if _session_manager == None:
        _session_manager = SessionManager()
    return _session_manager
