# Copyright (C) 2015 Martin Abente Lahaye <tch@sugarlabs.org>
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

    MONITOR_RATE = 1000
    TIMEOUT_DELAY = 1000
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
        self._start_monitoring()
        self._restore()

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

        self._monitor = Gio.File.new_for_path(self.get_path()) \
            .monitor_file(Gio.FileMonitorFlags.WATCH_HARD_LINKS, None)
        self._monitor.set_rate_limit(self.MONITOR_RATE)
        self._monitor_changed_hid = \
            self._monitor.connect('changed', self.__monitor_changed_cb)

    def _get_helper(self):
        if self._helper_path is None and 'PATH' in os.environ:
            for path in os.environ['PATH'].split(os.pathsep):
                helper_path = os.path.join(path, 'sugar-backlight-helper')
                if os.path.exists(helper_path):
                    self._helper_path = helper_path
                    break
        return self._helper_path

    def _helper_read(self, option):
        cmd = '%s --%s' % (self._get_helper(), option)
        result, output, error, status = GLib.spawn_command_line_sync(cmd)
        if status != 0:
            return None
        return output.rstrip('\0\n')

    def _helper_write(self, option, value):
        cmd = 'pkexec %s --%s %d' % (self._get_helper(), option, value)
        result, output, error, status = GLib.spawn_command_line_sync(cmd)

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
        if self._monitor_timeout_id is None:
            self._monitor.handler_block(self._monitor_changed_hid)

        self._helper_write('set-brightness', value)
        self.changed_signal.emit(value)

        # do monitor again only after the rate has passed
        if self._monitor_timeout_id is not None:
            GLib.source_remove(self._monitor_timeout_id)
        self._monitor_timeout_id = GLib.timeout_add(
            self.MONITOR_RATE * 2, self.__monitor_timeout_cb)

        # do not store every change while is still changing
        if self._save_timeout_id is not None:
            GLib.source_remove(self._save_timeout_id)
        self._save_timeout_id = GLib.timeout_add(
            self.TIMEOUT_DELAY, self.__save_timeout_cb, value)

    def get_path(self):
        if self._path is None:
            self._path = str(self._helper_read('get-path'))
        return self._path

    def get_brightness(self):
        return int(self._helper_read('get-brightness'))

    def get_max_brightness(self):
        if self._max_brightness is None:
            self._max_brightness = int(self._helper_read('get-max-brightness'))
        return self._max_brightness
