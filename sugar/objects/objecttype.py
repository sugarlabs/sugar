_SERVICE = "org.laptop.ObjectTypeRegistry"
_PATH = "/org/laptop/ObjectTypeRegistry"
_IFACE = "org.laptop.ObjectTypeRegistry"

def _object_type_from_dict(info_dict):
    if info_dict:
        return ObjectType(info_dict['type_id'],
                          info_dict['name'],
                          info_dict['icon'])
    else:
        return None

class ObjectType(object):
    def __init__(self, type_id, name, icon, mime_types):
        self.type_id = type_id
        self.name = name
        self.icon = icon
        self.mime_types = []

    def to_dict(self):
        return { 'type_id' : self.type_id,
                 'name'    : self.name,
                 'icon'    : self.icon
                }

class ObjectTypeRegistry(object):
    def __init__(self):
        bus = dbus.SessionBus()
        bus_object = bus.get_object(_SERVICE, _PATH)
        self._registry = dbus.Interface(bus_object, _IFACE)

    def get_type(type_id):
        type_dict = self._registry.GetType(type_id)
        return _object_type_from_dict(type_dict)

    def get_type_for_mime(mime_type):
        type_dict = self._registry.GetTypeForMime(type_id)
        return _object_type_from_dict(type_dict)

_registry = ObjectRegistry()

def get_registry():
    return _registry
