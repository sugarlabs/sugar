# Copyright (C) 2006-2007 Red Hat, Inc.
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
    """Data structure storing simple activity metadata"""
    def __init__(
        self, activity_id, pservice_id=None,
        object_id=None,uri=None
    ):
        """Initialise the handle from activity_id
        
        activity_id -- unique id for the activity to be
            created
        pservice_id -- identity of the sharing service 
            for this activity in the PresenceService
        object_id -- identity of the journal object 
            associated with the activity. It was used by 
            the journal prototype implementation, might 
            change when we do the real one. 
            
            When you resume an activity from the journal 
            the object_id will be passed in. It's optional 
            since new activities does not have an 
            associated object (yet).
            
            XXX Not clear how this relates to the activity
            id yet, i.e. not sure we really need both. TBF
        uri -- URI associated with the activity. Used when 
            opening an external file or resource in the 
            activity, rather than a journal object 
            (downloads stored on the file system for 
            example or web pages)
        """
        self.activity_id = activity_id
        self.pservice_id = pservice_id
        self.object_id = object_id
        self.uri = uri

    def get_shared_activity(self):
        """Retrieve the shared instance of this activity
        
        Uses the PresenceService to find any existing dbus 
        service which provides sharing mechanisms for this 
        activity.
        """
        if self.pservice_id:
            pservice = presenceservice.get_instance()
            return pservice.get_activity(self.pservice_id)
        else:
            return None

    def get_dict(self):
        """Retrieve our settings as a dictionary"""
        result = { 'activity_id' : self.activity_id }
        if self.pservice_id:
            result['pservice_id'] = self.pservice_id
        if self.object_id:
            result['object_id'] = self.object_id
        if self.uri:
            result['uri'] = self.uri

        return result

def create_from_dict(handle_dict):
    """Create a handle from a dictionary of parameters"""
    result = ActivityHandle(
        handle_dict['activity_id'],
        pservice_id = handle_dict.get( 'pservice_id' ),
        object_id = handle_dict.get('object_id'),
        uri = handle_dict.get('uri'),
    )
    return result
