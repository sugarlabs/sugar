# Copyright (C) 2008, Red Hat, Inc.
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

from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import SugarExt
import dbus
import os
import logging

from jarabe.model import shell


_session_manager = None


def have_systemd():
    return os.access("/run/systemd/seats", os.F_OK)


class SessionManager(GObject.GObject):

    shutdown_signal = GObject.Signal('shutdown')

    MODE_LOGOUT = 0
    MODE_SHUTDOWN = 1
    MODE_REBOOT = 2

    SHUTDOWN_TIMEOUT = 1
    MAX_SHUTDOWN_TRIES = 10

    def __init__(self):
        GObject.GObject.__init__(self)

        address = SugarExt.xsmp_init()
        os.environ['SESSION_MANAGER'] = address
        SugarExt.xsmp_run()

        self.session = SugarExt.Session.create_global()
        self._shell_model = shell.get_model()
        self._shutdown_tries = 0
        self._logout_mode = None

    def start(self):
        self.session.start()
        self.session.connect('shutdown_completed',
                             self.__shutdown_completed_cb)

    def initiate_shutdown(self, logout_mode):
        self._logout_mode = logout_mode
        self.shutdown_signal.emit()
        self.session.initiate_shutdown()

    def cancel_shutdown(self):
        self.session.cancel_shutdown()
        self._shutdown_tries = 0
        self._logout_mode = None

    def __shutdown_completed_cb(self, session):
        if self._logout_mode is not None:
            if self._try_shutdown():
                GObject.timeout_add(self.SHUTDOWN_TIMEOUT, self._try_shutdown)

    def _try_shutdown(self):
        if len(self._shell_model) > 0:
            self._shutdown_tries += 1
            if self._shutdown_tries < self.MAX_SHUTDOWN_TRIES:
                # returning True, the timeout_add_seconds will try
                # again in the specified seconds
                return True

        self.shutdown_completed()
        return False

    def logout(self):
        self.initiate_shutdown(self.MODE_LOGOUT)

    def shutdown(self):
        self.initiate_shutdown(self.MODE_SHUTDOWN)

    def reboot(self):
        self.initiate_shutdown(self.MODE_REBOOT)

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

        SugarExt.xsmp_shutdown()
        Gtk.main_quit()


def get_session_manager():
    global _session_manager

    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
