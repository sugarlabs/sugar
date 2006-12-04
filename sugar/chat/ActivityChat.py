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

from sugar.chat.GroupChat import GroupChat

class ActivityChat(GroupChat):
    SERVICE_TYPE = "_olpc_activity_chat._udp"

    def __init__(self, activity):
        GroupChat.__init__(self)
        self._chat_service = None

        self.connect('destroy', self._destroy_cb)

        self._activity = activity
        self._pservice.register_service_type(ActivityChat.SERVICE_TYPE)
        self._pservice.connect('service-appeared', self._service_appeared_cb)

        # Find an existing activity chat to latch onto
        ps_activity = self._pservice.get_activity(activity.get_id())
        if ps_activity is not None:
            services = ps_activity.get_services_of_type(ActivityChat.SERVICE_TYPE)
            if len(services) > 0:
                self._service_appeared_cb(self._pservice, services[0])

    def _service_appeared_cb(self, pservice, service):
        if service.get_activity_id() != self._activity.get_id():
            return
        if service.get_type() != ActivityChat.SERVICE_TYPE:
            return
        if self._chat_service:
            return

        logging.debug('Activity chat service appeared, setup the stream.')
        # Ok, there's an existing chat service that we copy
        # parameters and such from
        addr = service.get_address()
        port = service.get_port()
        self._chat_service = self._pservice.share_activity(self._activity,
                stype=ActivityChat.SERVICE_TYPE, address=addr, port=port)
        self._setup_stream(self._chat_service)

    def share(self):
        """Only called when we share the activity this chat is tied to."""
        self._chat_service = self._pservice.share_activity(self._activity,
                stype=ActivityChat.SERVICE_TYPE)
        self._setup_stream(self._chat_service)

    def _destroy_cb(self, widget):
        if self._chat_service:
            self._pservice.unregister_service(self._chat_service)
