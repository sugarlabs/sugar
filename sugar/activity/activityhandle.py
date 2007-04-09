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

from sugar.presence import presenceservice

class ActivityHandle(object):
    def __init__(self, activity_id):
        self.activity_id = activity_id
        self.pservice_id = None
        self.object_id = None
        self.uri = None

    def get_presence_service(self):
        if self.pservice_id:
            pservice = presenceservice.get_instance()
            return pservice.get_activity(self.pservice_id)
        else:
            return None

    def get_dict(self):
        result = { 'activity_id' : self.activity_id }
        if self.pservice_id:
            result['pservice_id'] = self.pservice_id
        if self.object_id:
            result['object_id'] = self.object_id
        if self.uri:
            result['uri'] = self.uri

        return result

def create_from_dict(handle_dict):
    result = ActivityHandle(handle_dict['activity_id'])
    if handle_dict.has_key('pservice_id'):
        result.pservice_id = handle_dict['pservice_id']
    if handle_dict.has_key('object_id'):
        result.object_id = handle_dict['object_id']
    if handle_dict.has_key('uri'):
        result.uri = handle_dict['uri']

    return result
