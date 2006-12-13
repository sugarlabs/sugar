class ClipboardObject:

    def __init__(self, id, name):
        self._id = id
        self._name = name
        self._percent = 0
        self._formats = {}
            
    def get_id(self):
        return self._id
    
    def get_name(self):
        return self._name

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
