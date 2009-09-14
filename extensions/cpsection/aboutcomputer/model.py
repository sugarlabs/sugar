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
#

import os
import logging
import re
import subprocess
from gettext import gettext as _
import errno

from jarabe import config

_logger = logging.getLogger('ControlPanel - AboutComputer')
_not_available = _('Not available')

def get_aboutcomputer():
    msg = 'Serial Number: %s \nBuild Number: %s \nFirmware Number: %s \n' \
            % (get_serial_number(), get_build_number(), get_firmware_number())
    return msg

def print_aboutcomputer():
    print get_aboutcomputer()

def get_serial_number():
    serial_no = _read_file('/ofw/serial-number')
    if serial_no is None:
        serial_no = _not_available
    return serial_no
    
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

    if build_no is None or not build_no:
        build_no = _not_available

    return build_no

def print_build_number():
    print get_build_number()

def get_firmware_number():    
    firmware_no = _read_file('/ofw/openprom/model')
    if firmware_no is None:
        firmware_no = _not_available
    else:
        firmware_no = re.split(" +", firmware_no)
        if len(firmware_no) == 3:
            firmware_no = firmware_no[1]
    return firmware_no        

def print_firmware_number():    
    print get_firmware_number()

def get_wireless_firmware():
    try:
        info = subprocess.Popen(["/usr/sbin/ethtool", "-i", "eth0"],
                                stdout=subprocess.PIPE).stdout.readlines()
    except OSError:
        return _not_available
    try:
        wireless_firmware = [line for line in info
                             if line.startswith('firmware')][0].split()[1]
    except IndexError:
        wireless_firmware = _not_available
    return wireless_firmware

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
    license_file = os.path.join(config.data_path, 'GPLv2')
    lang = os.environ['LANG']
    if lang.endswith("UTF-8"):
        lang = lang[:-6]

    try_file = license_file + "." + lang
    if os.path.isfile(try_file):
        license_file = try_file
    else:
        try_file = license_file + "." + lang.split("_")[0]
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
