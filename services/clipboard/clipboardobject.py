import typeregistry

class ClipboardObject:

    def __init__(self, object_path, name):
        self._id = object_path
        self._name = name
        self._percent = 0
        self._formats = {}

    def get_id(self):
        return self._id

    def _get_type_info(self):
        type_registry = typeregistry.get_instance()
        return type_registry.get_type(self._formats)
    
    def get_name(self):
        if self._name:
            return self._name
        else:
            return self._get_type_info().get_name()

    def get_icon(self):
        return self._get_type_info().get_icon()

    def get_preview(self):
        return self._get_type_info().get_preview()

    def get_activity(self):
        return self._get_type_info().get_activity()
        
    def get_percent(self):
        return self._percent

    def set_percent(self, percent):
        self._percent = percent
    
    def add_format(self, format):
        self._formats[format.get_type()] = format
    
    def get_formats(self):
        return self._formats
        
class Format:

    def __init__(self, type, data, on_disk):
        self._type = type
        self._data = data
        self._on_disk = on_disk

    def get_type(self):
        return self._type

    def get_data(self):
        return self._data

    def _set_data(self, data):
        self._data = data

    def get_on_disk(self):
        return self._on_disk
