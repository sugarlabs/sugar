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
import dbus


_HARDWARE_MANAGER_INTERFACE = 'org.freedesktop.ohm.Keystore'
_HARDWARE_MANAGER_SERVICE = 'org.freedesktop.ohm'
_HARDWARE_MANAGER_OBJECT_PATH = '/org/freedesktop/ohm/Keystore'

POWERD_FLAG_DIR = '/etc/powerd/flags'


def using_powerd():
    return os.access(POWERD_FLAG_DIR, os.W_OK)


def _get_ohm():
    bus = dbus.SystemBus()
    proxy = bus.get_object(_HARDWARE_MANAGER_SERVICE,
                           _HARDWARE_MANAGER_OBJECT_PATH,
                           follow_name_owner_changes=True)
    return dbus.Interface(proxy, _HARDWARE_MANAGER_INTERFACE)


def unfreeze():
    if not using_powerd():
        return

    try:
        _get_ohm().SetKey('display.dcon_freeze', 0)
    except dbus.DBusException:
        pass
