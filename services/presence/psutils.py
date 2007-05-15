# Copyright (C) 2007, Red Hat, Inc.
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

import dbus, dbus.glib, gobject
import logging


_logger = logging.getLogger('s-p-s.psutils')


def bytes_to_string(bytes):
    """The function converts a  D-BUS byte array provided by dbus to string format.
    
    bytes -- a D-Bus array of bytes. Handle both DBus byte arrays and strings
    
    """
    try:
        # DBus Byte array
        ret = ''.join([chr(item) for item in bytes])
    except TypeError:
        # Python string
        ret = ''.join([str(item) for item in bytes])
    return ret


NM_SERVICE = 'org.freedesktop.NetworkManager'
NM_IFACE = 'org.freedesktop.NetworkManager'
NM_IFACE_DEVICES = 'org.freedesktop.NetworkManager.Devices'
NM_PATH = '/org/freedesktop/NetworkManager'

_ip4am = None

class IP4AddressMonitor(gobject.GObject):
    """This class, and direct buddy IPv4 address access, will go away quite soon"""

    __gsignals__ = {
        'address-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                               ([gobject.TYPE_PYOBJECT]))
    }

    __gproperties__ = {
        'address' : (str, None, None, None, gobject.PARAM_READABLE)
    }

    def get_instance():
        """Retrieve (or create) the IP4Address monitor singleton instance"""
        global _ip4am
        if not _ip4am:
            _ip4am = IP4AddressMonitor()
        return _ip4am
    get_instance = staticmethod(get_instance)

    def __init__(self):
        gobject.GObject.__init__(self)
        self._nm_present = False
        self._matches = []
        self._addr = None
        self._nm_obj = None

        sys_bus = dbus.SystemBus()
        bus_object = sys_bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
        try:
            if bus_object.GetNameOwner(NM_SERVICE, dbus_interface='org.freedesktop.DBus'):
                self._nm_present = True
        except dbus.DBusException:
            pass

        if self._nm_present:
            self._connect_to_nm()
        else:
            addr = self._get_address_fallback()
            self._update_address(addr)

    def do_get_property(self, pspec):
        if pspec.name == "address":
            return self._addr

    def _update_address(self, new_addr):
        if new_addr == "0.0.0.0":
            new_addr = None
        if new_addr == self._addr:
            return

        self._addr = new_addr
        _logger.debug("IP4 address now '%s'" % new_addr)
        self.emit('address-changed', new_addr)

    def _connect_to_nm(self):
        """Connect to NM device state signals to tell when the IPv4 address changes"""
        try:
            sys_bus = dbus.SystemBus()
            proxy = sys_bus.get_object(NM_SERVICE, NM_PATH)
            self._nm_obj = dbus.Interface(proxy, NM_IFACE)
        except dbus.DBusException, err:
            _logger.debug("Error finding NetworkManager: %s" % err)
            self._nm_present = False
            return

        sys_bus = dbus.SystemBus()
        match = sys_bus.add_signal_receiver(self._nm_device_active_cb,
                                            signal_name="DeviceNowActive",
                                            dbus_interface=NM_IFACE)
        self._matches.append(match)

        match = sys_bus.add_signal_receiver(self._nm_device_no_longer_active_cb,
                                            signal_name="DeviceNoLongerActive",
                                            dbus_interface=NM_IFACE,
                                            bus_name=NM_SERVICE)
        self._matches.append(match)

        match = sys_bus.add_signal_receiver(self._nm_state_change_cb,
                                            signal_name="StateChange",
                                            dbus_interface=NM_IFACE,
                                            bus_name=NM_SERVICE)
        self._matches.append(match)

        state = self._nm_obj.state()
        if state == 3: # NM_STATE_CONNECTED
            self._query_devices()

    def _device_properties_cb(self, *props):        
        active = props[4]
        if not active:
            return
        act_stage = props[5]
        # HACK: OLPC NM has an extra stage, so activated == 8 on OLPC
        # but 7 everywhere else
        if act_stage != 8 and act_stage != 7:
            # not activated
            return
        self._update_address(props[6])

    def _device_properties_error_cb(self, err):
        _logger.debug("Error querying device properties: %s" % err)

    def _query_device_properties(self, device):
        sys_bus = dbus.SystemBus()
        proxy = sys_bus.get_object(NM_SERVICE, device)
        dev = dbus.Interface(proxy, NM_IFACE_DEVICES)
        dev.getProperties(reply_handler=self._device_properties_cb,
                          error_handler=self._device_properties_error_cb)

    def _get_devices_cb(self, ops):
        """Query each device's properties"""
        for op in ops:
            self._query_device_properties(op)

    def _get_devices_error_cb(self, err):
        _logger.debug("Error getting NetworkManager devices: %s" % err)

    def _query_devices(self):
        """Query NM for a list of network devices"""
        self._nm_obj.getDevices(reply_handler=self._get_devices_cb,
                                error_handler=self._get_devices_error_cb)

    def _nm_device_active_cb(self, device, ssid=None):
        self._query_device_properties(device)

    def _nm_device_no_longer_active_cb(self, device):
        self._update_address(None)

    def _nm_state_change_cb(self, new_state):
        if new_state == 4: # NM_STATE_DISCONNECTED
            self._update_address(None)

    def handle_name_owner_changed(self, name, old, new):
        """Clear state when NM goes away"""
        if name != NM_SERVICE:
            return
        if (old and len(old)) and (not new and not len(new)):
            # NM went away
            self._nm_present = False
            for match in self._matches:
                match.remove()
            self._matches = []
            self._update_address(None)
        elif (not old and not len(old)) and (new and len(new)):
            # NM started up
            self._nm_present = True
            self._connect_to_nm()

    def _get_iface_address(self, iface):
        import socket
        import fcntl
        import struct
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        fd = s.fileno()
        SIOCGIFADDR = 0x8915
        addr = fcntl.ioctl(fd, SIOCGIFADDR, struct.pack('256s', iface[:15]))[20:24]
        s.close()
        return socket.inet_ntoa(addr)

    def _get_address_fallback(self):
        import commands
        (s, o) = commands.getstatusoutput("/sbin/route -n")
        if s != 0:
            return
        for line in o.split('\n'):
            fields = line.split(" ")
            if fields[0] == "0.0.0.0":
                iface = fields[len(fields) - 1]
                return self._get_iface_address(iface)
        return None
