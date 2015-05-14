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

    _STEPS = 20
    _SUGAR_LINK = '/var/run/sugar-backlight'
    _SAVE_DELAY = 1000
    changed_signal = GObject.Signal('changed', arg_types=([int]))

    def __init__(self):
        GObject.GObject.__init__(self)
        self._path = None
        self._helper_path = None
        self._max_brightness = None
        self._save_timeout_id = None
        self._setup()
        self._restore()

    def _setup(self):
        cmd = 'pkexec %s' % self._find_binary('sugar-backlight-setup')
        GLib.spawn_command_line_sync(cmd)

    def _save(self, value):
        settings = Gio.Settings('org.sugarlabs.screen')
        settings.set_int('brightness', value)

    def _restore(self):
        settings = Gio.Settings('org.sugarlabs.screen')
        value = settings.get_int('brightness')
        if value != -1:
            self.set_brightness(value)

    def _get_helper(self):
        if self._helper_path is None:
            self._helper_path = self._find_binary('sugar-backlight-helper')
        return self._helper_path

    def _find_binary(self, binary):
        for path in os.environ['PATH'].split(os.pathsep):
            binary_path = os.path.join(path, binary)
            if os.path.exists(binary_path):
                return binary_path
        return None

    def _helper_read(self, option):
        cmd = '%s --%s' % (self._get_helper(), option)
        result, output, error, status = GLib.spawn_command_line_sync(cmd)
        if status != 0:
            return None
        return output.rstrip('\0\n')

    def _helper_write(self, option, value):
        cmd = 'pkexec %s --%s %d' % (self._get_helper(), option, value)
        GLib.spawn_command_line_sync(cmd)

    def __save_timeout_cb(self, value):
        self._save_timeout_id = None
        self._save(value)
        return False

    def set_brightness(self, value):
        self._helper_write('set-brightness', value)
        self.changed_signal.emit(value)

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
