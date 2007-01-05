import logging

class FileType:
    def __init__(self, formats):
        self._formats = formats

    def get_name(self):
        raise NotImplementedError

    def get_icon(self):
        raise NotImplementedError

    def get_preview(self):
        raise NotImplementedError
        
    def matches_mime_type(cls, mime_type):
        raise NotImplementedError
    matches_mime_type = classmethod(matches_mime_type)

class TextFileType(FileType):

    _types = set(['text/plain', 'UTF8_STRING', 'STRING'])

    def get_name(self):
        return 'Text snippet'

    def get_icon(self):
        return 'activity-xbook'

    def get_preview(self):
        for format, data in self._formats.iteritems():
            if format in TextFileType._types:
                return str(data.get_data())

        return ''
        
    def matches_mime_type(cls, mime_type):
        return mime_type in cls._types
    matches_mime_type = classmethod(matches_mime_type)

class ImageFileType(FileType):

    _types = set(['image/jpeg', 'image/gif', 'image/png', 'image/tiff'])

    def get_name(self):
        return 'Image'

    def get_icon(self):
        return 'activity-sketch'

    def get_preview(self):
        return ''
        
    def matches_mime_type(cls, mime_type):
        return mime_type in cls._types
    matches_mime_type = classmethod(matches_mime_type)

class UriFileType(FileType):
    
    _types = set(['_NETSCAPE_URL'])
    
    def get_name(self):
        return 'URL'

    def get_icon(self):
        return 'activity-web'

    def get_preview(self):
        for format, data in self._formats.iteritems():
            if format in UriFileType._types:
                string = data.get_data()
                title = string.split("\n")[1]
                return title
        
        return ''
        
    def matches_mime_type(cls, mime_type):
        return mime_type in cls._types
    matches_mime_type = classmethod(matches_mime_type)

class PdfFileType(FileType):
    
    _types = set(['application/pdf'])
    
    def get_name(self):
        return 'PDF file'

    def get_icon(self):
        return 'activity-xbook'

    def get_preview(self):
        return ''
        
    def matches_mime_type(cls, mime_type):
        return mime_type in cls._types
    matches_mime_type = classmethod(matches_mime_type)

class MsWordFileType(FileType):
    
    _types = set(['application/msword'])
    
    def get_name(self):
        return 'MS Word file'

    def get_icon(self):
        return 'activity-abiword'

    def get_preview(self):
        return ''
        
    def matches_mime_type(cls, mime_type):
        return mime_type in cls._types
    matches_mime_type = classmethod(matches_mime_type)

class RtfFileType(FileType):
    
    _types = set(['application/rtf', 'text/rtf'])
    
    def get_name(self):
        return 'RTF file'

    def get_icon(self):
        return 'activity-abiword'

    def get_preview(self):
        return ''
        
    def matches_mime_type(cls, mime_type):
        return mime_type in cls._types
    matches_mime_type = classmethod(matches_mime_type)

class UnknownFileType(FileType):
    def get_name(self):
        return 'Object'

    def get_icon(self):
        return 'stock-missing'

    def get_preview(self):
        return ''
        
    def matches_mime_type(cls, mime_type):
        return true
    matches_mime_type = classmethod(matches_mime_type)

class TypeRegistry:
    def __init__(self):
        self._types = []
        self._types.append(PdfFileType)
        self._types.append(MsWordFileType)
        self._types.append(RtfFileType)
        self._types.append(UriFileType)
        self._types.append(ImageFileType)
        self._types.append(TextFileType)
    
    def get_type(self, formats):
        for file_type in self._types:
            for format, data in formats.iteritems():
                if file_type.matches_mime_type(format):
                    return file_type(formats)

        return UnknownFileType(formats)
    
_type_registry = None
def get_instance():
    global _type_registry
    if not _type_registry:
        _type_registry = TypeRegistry()
    return _type_registry
