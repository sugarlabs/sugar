# Copyright (C) 2007, Eduardo Silva <edsiper@gmail.com>
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

import socket
import fcntl
import struct
import string

class Device:
    def __init__(self):
        self._dev = self.get_interfaces()

    def get_interfaces(self):
        netdevfile = "/proc/net/dev"
        dev = []

        try:
            infile = file(netdevfile, "r")
        except: 
            print "Error trying " + netdevfile

        skip = 0
        for line in infile:
            # Skip first two lines
            skip += 1
            if skip <= 2:
                continue

            iface = string.split(line, ":",1)
            arr = string.split(iface[1])

            info = {'interface': iface[0].strip(), \
                'bytes_recv': arr[0],\
                'bytes_sent': arr[8],\
                'packets_recv': arr[1],
                'packets_sent': arr[9]}

            dev.append(info)
        return dev

    def get_iface_info(self, ifname):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        hwaddr = []
        try:
            ip = socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, \
                struct.pack('256s', ifname[:15]))[20:24])
        except:
            ip = None

        try:
            netmask = socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x891b, \
                struct.pack('256s', ifname[:15]))[20:24])
        except:
            netmask = None
            
        try:
            mac = []
            info = fcntl.ioctl(s.fileno(), 0x8927, \
                struct.pack('256s', ifname[:15]))
            for char in info[18:24]:
                hdigit = hex(ord(char))[2:]
                if len(hdigit):
                    mac.append(hdigit)
        except:
            mac = None

        mac_string = self.mac_to_string(mac)
        return [ip, netmask, mac_string]

    def mac_to_string(self, hexa):
        string = ''
        for value in hexa:
            if len(string)==0:
                string = value
            else:
                string += ':'+value

        return string
