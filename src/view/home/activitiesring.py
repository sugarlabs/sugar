# Copyright (C) 2006-2007 Red Hat, Inc.
# Copyright (C) 2008 One Laptop Per Child
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
import logging
import signal
from gettext import gettext as _
import re

import gobject
import gtk
import hippo
import dbus

from hardware import hardwaremanager
from sugar.graphics import style
from sugar.graphics.palette import Palette
from sugar.profile import get_profile
from sugar import env

from view.home.MyIcon import MyIcon
from model.shellmodel import ShellModel
from hardware import schoolserver

_logger = logging.getLogger('ActivitiesRing')

class ActivitiesRing(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'SugarActivitiesRing'

    def __init__(self, shell):
        hippo.CanvasBox.__init__(self, background_color=0xe2e2e2ff)

        shell_model = shell.get_model()

        self._my_icon = _MyIcon(shell, style.XLARGE_ICON_SIZE)
        self.append(self._my_icon, hippo.PACK_FIXED)

        shell_model.connect('notify::state',
                            self._shell_state_changed_cb)

    def _shell_state_changed_cb(self, model, pspec):
        # FIXME implement this
        if model.props.state == ShellModel.STATE_SHUTDOWN:
            pass

    def do_allocate(self, width, height, origin_changed):
        hippo.CanvasBox.do_allocate(self, width, height, origin_changed)

        [icon_width, icon_height] = self._my_icon.get_allocation()
        self.set_position(self._my_icon, (width - icon_width) / 2,
                          (height - icon_height) / 2)

    def enable_xo_palette(self):
        self._my_icon.enable_palette()

class _MyIcon(MyIcon):
    def __init__(self, shell, scale):
        MyIcon.__init__(self, scale)

        self._power_manager = None
        self._shell = shell
        self._profile = get_profile()

    def enable_palette(self):
        palette = Palette(self._profile.nick_name)

        item = gtk.MenuItem(_('Reboot'))
        item.connect('activate', self._reboot_activate_cb)
        palette.menu.append(item)
        item.show()

        item = gtk.MenuItem(_('Shutdown'))
        item.connect('activate', self._shutdown_activate_cb)
        palette.menu.append(item)
        item.show()

        if not self._profile.is_registered():
            item = gtk.MenuItem(_('Register'))
            item.connect('activate', self._register_activate_cb)
            palette.menu.append(item)
            item.show()
 
        item = gtk.MenuItem(_('About this XO'))
        item.connect('activate', self._about_activate_cb)
        palette.menu.append(item)
        item.show()

        self.set_palette(palette)

    def _reboot_activate_cb(self, menuitem):
        model = self._shell.get_model()
        model.props.state = ShellModel.STATE_SHUTDOWN

        pm = self._get_power_manager()

        hw_manager = hardwaremanager.get_manager()
        hw_manager.shutdown()

        if env.is_emulator():
            self._close_emulator()
        else:
            pm.Reboot()

    def _shutdown_activate_cb(self, menuitem):
        model = self._shell.get_model()
        model.props.state = ShellModel.STATE_SHUTDOWN

        pm = self._get_power_manager()

        hw_manager = hardwaremanager.get_manager()
        hw_manager.shutdown()

        if env.is_emulator():
            self._close_emulator()
        else:
            pm.Shutdown()

    def _register_activate_cb(self, menuitem):
        schoolserver.register_laptop()
        if self._profile.is_registered():
            self.get_palette().menu.remove(menuitem)

    def _about_activate_cb(self, menuitem):        
        dialog = gtk.Dialog(_('About this XO'),
                            self.palette,
                            gtk.DIALOG_MODAL | 
                            gtk.DIALOG_DESTROY_WITH_PARENT,
                            (gtk.STOCK_OK, gtk.RESPONSE_OK))

        not_available = _('Not available')
        build = self._read_file('/boot/olpc_build')
        if build is None:
            build = not_available
        label_build = gtk.Label('Build: %s' % build)
        label_build.set_alignment(0, 0.5)
        label_build.show()
        dialog.vbox.pack_start(label_build)
                
        firmware = self._read_file('/ofw/openprom/model')
        if firmware is None:
            firmware = not_available
        else:
            firmware = re.split(" +", firmware)
            if len(firmware) == 3:
                firmware = firmware[1]
        label_firmware = gtk.Label('Firmware: %s' % firmware)
        label_firmware.set_alignment(0, 0.5)
        label_firmware.show()
        dialog.vbox.pack_start(label_firmware)
                
        serial = self._read_file('/ofw/serial-number')
        if serial is None:
            serial = not_available
        label_serial = gtk.Label('Serial Number: %s' % serial)
        label_serial.set_alignment(0, 0.5)
        label_serial.show()
        dialog.vbox.pack_start(label_serial)

        dialog.set_default_response(gtk.RESPONSE_OK)
        dialog.connect('response', self._response_cb)
        dialog.show()

    def _read_file(self, path):
        if os.access(path, os.R_OK) == 0:
            _logger.error('read_file() No such file or directory: %s', path)
            return None
        
        fd = open(path, 'r')
        value = fd.read()
        fd.close()            
        if value:
            value = value.strip('\n')
            return value
        else:
            _logger.error('read_file() No information in file or directory: %s', path)
            return None

    def _response_cb(self, widget, response_id):
        if response_id == gtk.RESPONSE_OK:            
            widget.destroy()

    def _close_emulator(self):
        if os.environ.has_key('SUGAR_EMULATOR_PID'):
            pid = int(os.environ['SUGAR_EMULATOR_PID'])
            os.kill(pid, signal.SIGTERM)

    def _get_power_manager(self):
        if self._power_manager is None:
            bus = dbus.SystemBus()
            proxy = bus.get_object('org.freedesktop.Hal', 
                                '/org/freedesktop/Hal/devices/computer')
            self._power_manager = dbus.Interface(proxy, \
                            'org.freedesktop.Hal.Device.SystemPowerManagement') 

        return self._power_manager

