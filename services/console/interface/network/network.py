# Copyright (C) 2007, Eduardo Silva <edsiper@gmail.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import gobject
from net.device import Device
from ui.treeview import TreeView

class NetworkView(TreeView):
    def __init__(self):
        col_names = []
        col_names.append({'index': 0, 'name': 'Interface'})
        col_names.append({'index': 1, 'name': 'IP Address'})
        col_names.append({'index': 2, 'name': 'NetMask'})
        col_names.append({'index': 3, 'name': 'MAC Address'})
        col_names.append({'index': 4, 'name': 'Bytes Recv'})
        col_names.append({'index': 5, 'name': 'Bytes Sent'})
        col_names.append({'index': 6, 'name': 'Packets Recv'})
        col_names.append({'index': 7, 'name': 'Packets Sent'})

        self._iface_iter = []
        cols_type = [str, str, str, str, str, str, str, str]
        TreeView.__init__(self, cols_type, col_names)

        self._dev = Device()
        self.show_all()
        gobject.timeout_add(1500, self._update_data)

    def _update_data(self):
        interfaces = self._dev.get_interfaces()        
        for iface in interfaces:
            info = self._dev.get_iface_info(iface['interface'])
            row = []
            row.append({'index':0, 'info': iface['interface']})
            
            if info[0]:
                row.append({'index':1, 'info': info[0]})
            if info[1]:
                row.append({'index':2, 'info': info[1]})
            if info[2]:
                row.append({'index':3, 'info': info[2]})

            row.append({'index': 4, 'info': iface['bytes_sent']})
            row.append({'index': 5, 'info': iface['packets_sent']})
            row.append({'index': 6, 'info': iface['bytes_recv']})
            row.append({'index': 7, 'info': iface['packets_recv']})

            iter = self._get_iface_iter(iface['interface'])
            if not iter:
                iter = self.add_row(row)
                self._set_iface_iter(iter, iface['interface'])
            else:
                self.update_row(iter, row)

        self._clear_down_interfaces(interfaces)
        return True

    def _set_iface_iter(self, iter, iface):
        self._iface_iter.append([iter, iface])

    def _remove_iface_iter(self, search_iter):
        i = 0
        for [iter, interface] in self._iface_iter:
            if iter == search_iter:
                del self._iface_iter[i]
                return
            i+=1

    def _get_iface_iter(self, iface):
        for [iter, interface] in self._iface_iter:
            if iface == interface:
                return iter

        return None

    def _clear_down_interfaces(self, interfaces):
        for [iter, iface] in self._iface_iter:
            found = False
            for dev in interfaces:
                if dev['interface']==iface:
                    found = True
                    break

            if not found:
                self.remove_row(iter)
                self._remove_iface_iter(iter)

class Interface(object):
    def __init__(self):
        self.widget = NetworkView()
