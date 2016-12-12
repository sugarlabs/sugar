# Copyright (C) 2015 Martin Abente Lahaye <tch@sugarlabs.org>
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

from gi.repository import GLib
from gi.repository import Gio
from gi.repository import GObject


_instance = None


def get_instance():
    global _instance
    if _instance is None:
        _instance = Brightness()
    return _instance


class Brightness(GObject.GObject):

    _STEPS = 20
    _SUGAR_LINK = '/var/run/sugar-backlight'
    _SAVE_DELAY = 1000
    _MONITOR_RATE = 1000
    changed_signal = GObject.Signal('changed', arg_types=([int]))

    def __init__(self):
        GObject.GObject.__init__(self)
        self._path = None
        self._helper_path = None
        self._max_brightness = None
        self._save_timeout_id = None
        self._monitor = None
        self._monitor_timeout_id = None
        self._monitor_changed_hid = None
        self._setup()
        self._start_monitoring()
        self._restore()

    def _setup(self):
        cmd = 'pkexec sugar-backlight-setup'
        GLib.spawn_command_line_sync(cmd)

    def _save(self, value):
        settings = Gio.Settings('org.sugarlabs.screen')
        settings.set_int('brightness', value)

    def _restore(self):
        settings = Gio.Settings('org.sugarlabs.screen')
        value = settings.get_int('brightness')
        if value != -1:
            self.set_brightness(value)

    def _start_monitoring(self):
        if not self.get_path():
            return

        path = os.path.join(self.get_path(), 'brightness')
        self._monitor = Gio.File.new_for_path(path) \
            .monitor_file(Gio.FileMonitorFlags.NONE, None)
        self._monitor.set_rate_limit(self._MONITOR_RATE)
        self._monitor_changed_hid = \
            self._monitor.connect('changed', self.__monitor_changed_cb)

    def _helper_read(self, option):
        cmd = 'sugar-backlight-helper --%s' % option
        result, output, error, status = GLib.spawn_command_line_sync(cmd)
        if status != 0:
            return None
        return output.rstrip('\0\n')

    def _helper_write(self, option, value):
        cmd = 'pkexec sugar-backlight-helper --%s %d' % (option, value)
        GLib.spawn_command_line_sync(cmd)

    def __monitor_changed_cb(self, monitor, child, other_file, event):
        if event == Gio.FileMonitorEvent.CHANGED:
            self.changed_signal.emit(self.get_brightness())

    def __monitor_timeout_cb(self):
        self._monitor_timeout_id = None
        self._monitor.handler_unblock(self._monitor_changed_hid)
        return False

    def __save_timeout_cb(self, value):
        self._save_timeout_id = None
        self._save(value)
        return False

    def set_brightness(self, value):
        # do not monitor the external change we are about to trigger
        if self._monitor is not None:
            if self._monitor_timeout_id is None:
                self._monitor.handler_block(self._monitor_changed_hid)

        self._helper_write('set-brightness', value)
        self.changed_signal.emit(value)

        # do monitor again only after the rate has passed
        if self._monitor is not None:
            if self._monitor_timeout_id is not None:
                GLib.source_remove(self._monitor_timeout_id)
            self._monitor_timeout_id = GLib.timeout_add(
                self._MONITOR_RATE * 2, self.__monitor_timeout_cb)

        # do not store every change while is still changing
        if self._save_timeout_id is not None:
            GLib.source_remove(self._save_timeout_id)
        self._save_timeout_id = GLib.timeout_add(
            self._SAVE_DELAY, self.__save_timeout_cb, value)

    def get_path(self):
        if self._path is None:
            if os.path.exists(self._SUGAR_LINK):
                self._path = self._SUGAR_LINK
        return self._path

    def get_brightness(self):
        return int(self._helper_read('get-brightness'))

    def get_max_brightness(self):
        if self._max_brightness is None:
            self._max_brightness = int(self._helper_read('get-max-brightness'))
        return self._max_brightness

    def get_step_amount(self):
        if self.get_max_brightness() < self._STEPS:
            return 1
        else:
            return self.get_max_brightness() / self._STEPS
