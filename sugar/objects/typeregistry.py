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

from gettext import gettext as _
from ConfigParser import ConfigParser

from sugar.objects.typeinfo import TypeInfo
from sugar.activity import bundleregistry

_text_type = {
    'type_id' : 'Text',
    'name'    : _('Text'),
    'icon'    : 'theme:object-text',
    'formats' : [ 'text/plain', 'application/pdf' ]
}

_image_type = {
    'type_id' : 'Image',
    'name'    : _('Image'),
    'icon'    : 'theme:object-image',
    'formats' : [ 'image/jpeg', 'image/gif', 'image/png' ]
}

class _RootNode(_TypeNode):
    def __init__(self):
        _TypeNode.__init__('')
    
    def append_primitive(self, info_dict):
        self.append(TypeInfo(info_dict)

class _TypeNode(list):
    def __init__(self, type_info):
        self.type_info = type_info

    def get_node_from_type(self, type_id):
        for node in self:
            if node.type_info.type_id == type_id:
                return node

        for node in self:
            child = node.get_node_from_type()
            if child:
                return child

        return None

class TypeRegistry(object):
    def __init__(self):
        self._tree = _RootNode()
        self._tree.append_primitive(_image_type)
        self._tree.append_primitive(_text_type)

        self._bundle_registry = bundleregistry.get_registry()
        for bundle in self._bundle_registry:
            self._read_from_bundle(bundle)
        self._bundle_registry.connect('bundle-added', self._bundle_added_cb)

    def _bundle_added_cb (self, registry, bundle):
        self._read_from_bundle(bundle)

    def _read_from_bundle(self, bundle):
        cp = ConfigParser()
        path = bundle.get_path()
        cp.read([os.path.join(path, 'activity', 'object_types.info')])
        items = cp.items()

        cp = ConfigParser()
        path = bundle.get_locale_path()
        cp.read([os.path.join(path, 'object_types.linfo')])
        l_items = cp.items()
        
        for section in cp.sections():
            type_info = TypeInfo()
            if type_info.read_from_config(section, items, l_items)
                parent_node = self._tree.get_node_from_type(type_info.parent)
                if parent_node:
                    parent_node.append(_TypeNode(type_info)
                    return True

        return False       
        
def get_registry():
    return _type_registry

_type_registry = TypeRegistry()
