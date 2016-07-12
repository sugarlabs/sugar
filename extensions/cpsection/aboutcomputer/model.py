# Copyright (C) 2008 One Laptop Per Child
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
#

import os
import logging
import subprocess
from gettext import gettext as _
import errno
import time

from gi.repository import Gio
from gi.repository import GLib

from jarabe import config
from jarabe.model.network import get_wireless_interfaces


_OFW_TREE = '/ofw'
_PROC_TREE = '/proc/device-tree'
_DMI_DIRECTORY = '/sys/class/dmi/id'

_logger = logging.getLogger('ControlPanel - AboutComputer')
_not_available = _('Not available')

_serial_no = None


def get_aboutcomputer():
    msg = 'Serial Number: %s \nBuild Number: %s \nFirmware Number: %s \n' \
        % (get_serial_number(), get_build_number(), get_firmware_number())
    return msg


def print_aboutcomputer():
    print get_aboutcomputer()


def _get_serial_number():
    serial_no = _read_device_tree('serial-number')
    if serial_no is not None:
        return serial_no

    cmd = 'pkexec sugar-serial-number-helper'
    result, output, error, status = GLib.spawn_command_line_sync(cmd)
    if status != 0:
        return _not_available

    return output.rstrip('\n')


def get_serial_number():
    global _serial_no

    if _serial_no is None:
        _serial_no = _get_serial_number()

    return _serial_no


def print_serial_number():
    serial_no = get_serial_number()
    if serial_no is None:
        serial_no = _not_available
    print serial_no


def get_build_number():
    build_no = _read_file('/boot/olpc_build')

    if build_no is None:
        build_no = _read_file('/etc/redhat-release')

    if build_no is None:
        try:
            popen = subprocess.Popen(['lsb_release', '-ds'],
                                     stdout=subprocess.PIPE)
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise
        else:
            build_no, stderr_ = popen.communicate()
            build_no = build_no.strip()

    if build_no is None or not build_no:
        build_no = _not_available

    return build_no


def print_build_number():
    print get_build_number()


def get_firmware_number():
    firmware_no = _read_device_tree('openprom/model')
    if firmware_no is not None:
        # try to extract Open Firmware version from OLPC style version
        # string, e.g. "CL2   Q4B11  Q4B"
        if firmware_no.startswith('CL'):
            firmware_no = firmware_no[6:13].strip()
        ec_name = _read_device_tree('ec-name')
        if ec_name:
            ec_name = ec_name.replace('Ver:', '')
            firmware_no = '%(firmware)s with %(ec)s' % {
                'firmware': firmware_no, 'ec': ec_name}

    elif os.path.exists(os.path.join(_DMI_DIRECTORY, 'bios_version')):
        firmware_no = _read_file(os.path.join(_DMI_DIRECTORY, 'bios_version'))
    if firmware_no is None:
        firmware_no = _not_available
    return firmware_no


def get_hardware_model():
    settings = Gio.Settings('org.sugarlabs.extensions.aboutcomputer')
    model = settings.get_string('hardware-model')
    if not model:
        model = _read_device_tree('mfg-data/MN')
        sku = _read_device_tree('mfg-data/sk')
        if sku:
            if sku.startswith('SKU'):
                model = '%s, %s' % (model, sku)
            else:
                model = '%s, SKU%s' % (model, sku)
    return model


def get_secondary_licenses():
    licenses = []
    # Check if there are more licenses to display
    licenses_path = config.licenses_path
    if os.path.isdir(licenses_path):
        for file_name in os.listdir(licenses_path):
            try:
                file_path = os.path.join(licenses_path, file_name)
                with open(file_path) as f:
                    licenses.append(f.read())
            except IOError:
                logging.error('Error trying open %s', file_path)
    return licenses


def print_firmware_number():
    print get_firmware_number()


def get_wireless_firmware():
    environment = os.environ.copy()
    environment['PATH'] = '%s:/usr/sbin' % (environment['PATH'], )
    firmware_info = {}

    wireless_interfaces = get_wireless_interfaces()
    if not wireless_interfaces:
        _logger.warning('Cannot connect to NetworkManager, falling back to'
                        ' static list of devices')
        wireless_interfaces = ['wlan0', 'eth0']

    for interface in get_wireless_interfaces():
        try:
            output = subprocess.Popen(['ethtool', '-i', interface],
                                      stdout=subprocess.PIPE,
                                      env=environment).stdout.readlines()
        except OSError:
            _logger.exception('Error running ethtool for %r', interface)
            continue

        try:
            for line in output:
                if line.startswith('firmware'):
                    version = line.split()[1]
                if line.startswith('driver'):
                    driver = line.split()[1]
        except IndexError:
            _logger.exception('Error parsing ethtool output for %r',
                              interface)
            continue

        card = None
        if driver == 'mwifiex':
            card = 'mv8787, IEEE 802.11n 5GHz'
        if driver == 'libertas':
            if version.startswith('5.'):
                card = 'usb8388, IEEE 802.11g 2.4GHz'
            else:
                card = 'mv8686, IEEE 802.11g 2.4GHz'

        if card:
            firmware_info[interface] = '%s (%s, %s)' % (version, driver, card)
        else:
            firmware_info[interface] = '%s (%s)' % (version, driver)

    if not firmware_info:
        return _not_available

    if len(firmware_info) == 1:
        return firmware_info.values()[0]

    return ', '.join(['%(interface)s: %(info)s' %
                      {'interface': interface, 'info': info}
                      for interface, info in firmware_info.items()])


def print_wireless_firmware():
    print get_wireless_firmware()


def _read_file(path):
    if os.access(path, os.R_OK) == 0:
        return None

    fd = open(path, 'r')
    value = fd.read()
    fd.close()
    if value:
        value = value.strip('\n')
        return value
    else:
        _logger.debug('No information in file or directory: %s', path)
        return None


def get_license():
    license_file = os.path.join(config.data_path, 'GPLv3')
    lang = os.environ['LANG']
    if lang.endswith('UTF-8'):
        lang = lang[:-6]

    try_file = license_file + '.' + lang
    if os.path.isfile(try_file):
        license_file = try_file
    else:
        try_file = license_file + '.' + lang.split('_')[0]
        if os.path.isfile(try_file):
            license_file = try_file

    try:
        fd = open(license_file)
        # remove 0x0c page breaks which can't be rendered in text views
        license_text = fd.read().replace('\x0c', '')
        fd.close()
    except IOError:
        license_text = _not_available
    return license_text


def _read_device_tree(path):
    value = _read_file(os.path.join(_PROC_TREE, path))
    if value:
        return value.strip('\x00')
    value = _read_file(os.path.join(_OFW_TREE, path))
    if value:
        return value.strip('\x00')
    return value


def days_from_last_update():

    last_update_seconds = -1
    # Get the number of seconds of the last update date.
    try:
        flag_file = '/var/lib/misc/last_os_update.stamp'
        if os.path.exists(flag_file):
            last_update_seconds = int(os.stat(flag_file).st_mtime)
    except IOError:
        _logger.error('couldn''t get last modification time')

    if last_update_seconds == -1:
        return -1

    now = time.time()
    days_from_last_update = (now - last_update_seconds) / (24 * 60 * 60)
    return int(days_from_last_update)
