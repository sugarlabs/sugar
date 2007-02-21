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

from sugar.presence import PresenceService

class ActivityHandle(object):
    def __init__(self, activity_id):
        self.activity_id = activity_id
        self.pservice_id = None

    def __str__(self):
        return self.activity_id

    def get_presence_service():
        pservice = PresenceService.get_instance()
        return pservice.get_activity(self._pservice_id)

def create_from_string(handle):
    activity_handle = ActivityHandle(handle)
    activity_handle.pservice_id = handle
