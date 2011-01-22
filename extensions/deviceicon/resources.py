# Copyright (C) Anish Mangal <anishmangal2002@gmail.com>
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

from gettext import gettext as _
import logging
import os

import gobject
import gtk
import gconf

from sugar.graphics.tray import TrayIcon
from sugar.graphics.xocolor import XoColor
from sugar.graphics.palette import Palette
from sugar.graphics import style


_SYSTEM_MOODS = ['-sad', '-normal', '-happy']
_ICON_NAME = 'computer'
_UPDATE_INTERVAL = 5*1000


class DeviceView(TrayIcon):

    FRAME_POSITION_RELATIVE = 500

    def __init__(self):
        client = gconf.client_get_default()
        self._color = XoColor(client.get_string('/desktop/sugar/user/color'))
        TrayIcon.__init__(self, icon_name=_ICON_NAME, xo_color=self._color)
        self.create_palette()
        self._icon_widget.connect('button-release-event', self._click_cb)

    def create_palette(self):
        self.palette = ResourcePalette(_('System resources'))
        self.palette.set_group_id('frame')
        self.palette.add_timer()
        self.palette.connect('system-mood-changed',
                self._system_mood_changed_cb)
        return self.palette

    def _system_mood_changed_cb(self, palette_, mood):
        self.icon.props.icon_name = _ICON_NAME + mood

    def _click_cb(self, widget, event):
        self.palette_invoker.notify_right_click()


class ResourcePalette(Palette):
    __gsignals__ = {
        'system-mood-changed': (gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE,
                           ([str])),
    }

    def __init__(self, primary_text):
        Palette.__init__(self, label=primary_text)

        self.vbox = gtk.VBox()
        self.set_content(self.vbox)

        self._cpu_text = gtk.Label()
        self.vbox.pack_start(self._cpu_text, padding=style.DEFAULT_PADDING)
        self._cpu_bar = gtk.ProgressBar()
        self._cpu_bar.set_size_request(
            style.zoom(style.GRID_CELL_SIZE * 4), -1)
        self.vbox.pack_start(self._cpu_bar, padding=style.DEFAULT_PADDING)

        self._memory_text = gtk.Label()
        self.vbox.pack_start(self._memory_text, padding=style.DEFAULT_PADDING)
        self._memory_bar = gtk.ProgressBar()
        self._memory_bar.set_size_request(
            style.zoom(style.GRID_CELL_SIZE * 4), -1)
        self.vbox.pack_start(self._memory_bar, padding=style.DEFAULT_PADDING)

        self._system_mood = None
        try:
            self._cpu_times = self._get_cpu_times_list()
        except IOError:
            logging.exception('An error ocurred while attempting to '
                'read /proc/stat')
            self._stop_computing_statistics()

        self.vbox.show()
        self._cpu_text.show()
        self._cpu_bar.show()
        self._memory_text.show()
        self._memory_bar.show()

    def add_timer(self):
        gobject.timeout_add(_UPDATE_INTERVAL, self.__timer_cb)

    def _get_cpu_times_list(self):
        """Return various cpu times as read from /proc/stat

        This method returns the following cpu times measured
        in jiffies (1/100 of a second for x86 systems)
        as an ordered list of numbers - [user, nice,
        system, idle, iowait] where,

        user: normal processes executing in user mode
        nice: niced processes executing in user mode
        system: processes executing in kernel mode
        idle: twiddling thumbs
        iowait: waiting for I/O to complete

        Note: For systems having 2 or more CPU's, the above
        numbers would be the cumulative sum of these times
        for all CPU's present in the system.

        """
        return [int(count)
           for count in file('/proc/stat').readline().split()[1:6]]

    def _percentage_cpu_available(self):
        """
        Return free CPU resources as a percentage

        """
        _cpu_times_new = self._get_cpu_times_list()
        _cpu_times_current = [(new - old)
            for new, old in zip(_cpu_times_new, self._cpu_times)]
        user_, nice_, system_, idle, iowait = _cpu_times_current
        cpu_free = (idle + iowait) * 100.0 / sum(_cpu_times_current)
        self._cpu_times = self._get_cpu_times_list()
        return cpu_free

    def _percentage_memory_available(self):
        """
        Return free memory as a percentage

        """
        for line in file('/proc/meminfo'):
            name, value, unit_ = line.split()[:3]
            if 'MemTotal:' == name:
                total = int(value)
            elif 'MemFree:' == name:
                free = int(value)
            elif 'Buffers:' == name:
                buffers = int(value)
            elif 'Cached:' == name:
                cached = int(value)
            elif 'Active:' == name:
                break
        return (free + buffers + cached) * 100.0 / total

    def __timer_cb(self):
        try:
            cpu_in_use = 100 - self._percentage_cpu_available()
            memory_in_use = 100 - self._percentage_memory_available()
        except IOError:
            logging.exception('An error ocurred while trying to '
                'retrieve resource usage statistics')
            self._stop_and_show_error()
            return False
        else:
            self._cpu_text.set_label(_('CPU in use: %d%%' % cpu_in_use))
            self._cpu_bar.set_fraction(float(cpu_in_use) / 100)
            self._memory_text.set_label(_('Memory in use: %d%%' %
                memory_in_use))
            self._memory_bar.set_fraction(float(memory_in_use) / 100)

            # both cpu_free and memory_free lie between 0-100
            system_mood = _SYSTEM_MOODS[
                    int(300 - (cpu_in_use + 2 * memory_in_use)) // 100]

            # check if self._system_mood exists
            try:
                if self._system_mood != system_mood:
                    self.emit('system-mood-changed', system_mood)
                    self._system_mood = system_mood
            except AttributeError:
                self.emit('system-mood-changed', system_mood)
                self._system_mood = system_mood

            return True

    def _stop_and_show_error(self):
        """
        Stop computing usage statistics and display an error message
        since we've hit an exception.

        """
        # Use the existing _cpu_text label to display the error. Remove
        # everything else.
        self._cpu_text.set_size_request(
            style.zoom(style.GRID_CELL_SIZE * 4), -1)
        self._cpu_text.set_line_wrap(True)
        self._cpu_text.set_text(_('Cannot compute CPU and memory usage '
            'statistics!'))
        self.vbox.remove(self._cpu_bar)
        self.vbox.remove(self._memory_text)
        self.vbox.remove(self._memory_bar)
        self.emit('system-mood-changed', '-error')


def setup(tray):
    if not (os.path.exists('/proc/stat') and os.path.exists('/proc/meminfo')):
        logging.warning('Either /proc/stat or /proc/meminfo not present. Not '
            'adding the CPU and memory usage icon to the frame')
        return
    tray.add_device(DeviceView())
