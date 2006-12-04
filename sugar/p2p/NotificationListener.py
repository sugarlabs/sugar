# Copyright (C) 2006, Red Hat, Inc.
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

import logging

from sugar.p2p.Notifier import Notifier
from sugar.p2p import network

class NotificationListener:
    def __init__(self, service):
        logging.debug('Start notification listener. Service %s, address %s, port %s' % (service.get_type(), service.get_address(), service.get_port()))
        server = network.GroupServer(service.get_address(),
                                     service.get_port(),
                                     self._recv_multicast)
        server.start()
        
        self._listeners = []
    
    def add_listener(self, listener):
        self._listeners.append(listener)
    
    def _recv_multicast(self, msg):
        for listener in self._listeners:
            listener(msg)
