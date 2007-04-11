# Copyright (C) 2007, Red Hat, Inc.
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

class TypeInfo(object):
    def __init__(self, info_dict=None):
        self.type_id = None
        self.name = None
        self.icon = 'theme:stock-missing'
        self.parent = None
        self.formats = []
        
        if info_dict:
            self._read_from_dict(info_dict)            

    def get_default_activity(self):
        return None
    
    def get_activities(self):
        return []

    def _read_from_config(self, section, items, l_items):
        self.type_id = section

        for item in items:
            if item[0] == 'name':
                self.name = item[1]
            elif item[0] == 'icon':
                self.icon = item[1]
            elif item[0] == 'parent':
                self.parent = item[1]            
            elif item[0] == 'formats':
                self.formats = item[1].split(';')
                
        for item in litems:
            if item[0] == 'name':
                self.name = item[1]
                
        return (self.name and self.parent and self.formats)
        
    def _read_from_dict(self, info_dict):
        self.type_id = info_dict['type_id']
        self.name = info_dict['name']
        self.icon = info_dict['icon']
        self.formats = info_dict['formats']
