import logging
from gettext import gettext as _

class FileType:
    def __init__(self, formats):
        self._formats = formats

    def get_name(self):
        raise NotImplementedError

    def get_icon(self):
        raise NotImplementedError

    def get_preview(self):
        raise NotImplementedError

    def get_activity(self):
        raise NotImplementedError
        
    def matches_mime_type(cls, mime_type):
        raise NotImplementedError
    matches_mime_type = classmethod(matches_mime_type)

class TextFileType(FileType):

    _types = set(['text/plain', 'UTF8_STRING', 'STRING'])

    def get_name(self):
        return _('Text snippet')

    def get_icon(self):
        return 'theme:activity-xbook'

    def get_preview(self):
        for format, data in self._formats.iteritems():
            if format in TextFileType._types:
                text = str(data.get_data())
                if len(text) < 50:
                    return text
                else:
                    return text[0:49] + "..."

        return ''

    def get_activity(self):
        return ''
        
    def matches_mime_type(cls, mime_type):
        return mime_type in cls._types
    matches_mime_type = classmethod(matches_mime_type)

class ImageFileType(FileType):

    _types = set(['image/jpeg', 'image/gif', 'image/png', 'image/tiff'])

    def get_name(self):
        return _('Image')

    def get_icon(self):
        return 'theme:activity-sketch'

    def get_preview(self):
        return ''

    def get_activity(self):
        return ''
        
    def matches_mime_type(cls, mime_type):
        return mime_type in cls._types
    matches_mime_type = classmethod(matches_mime_type)

class UriFileType(FileType):
    
    _types = set(['_NETSCAPE_URL'])
    
    def get_name(self):
        return _('Web Page')

    def get_icon(self):
        return 'theme:activity-web'

    def get_preview(self):
        for format, data in self._formats.iteritems():
            if format in UriFileType._types:
                string = data.get_data()
                title = string.split("\n")[1]
                return title
        
        return ''

    def get_activity(self):
        return ''

    def matches_mime_type(cls, mime_type):
        return mime_type in cls._types
    matches_mime_type = classmethod(matches_mime_type)

class PdfFileType(FileType):
    
    _types = set(['application/pdf'])
    
    def get_name(self):
        return _('PDF file')

    def get_icon(self):
        return 'theme:activity-xbook'

    def get_preview(self):
        return ''

    def get_activity(self):
        return 'org.laptop.sugar.Xbook'
        
    def matches_mime_type(cls, mime_type):
        return mime_type in cls._types
    matches_mime_type = classmethod(matches_mime_type)

class MsWordFileType(FileType):
    
    _types = set(['application/msword'])
    
    def get_name(self):
        return _('MS Word file')

    def get_icon(self):
        return 'theme:activity-abiword'

    def get_preview(self):
        return ''

    def get_activity(self):
        return 'org.laptop.AbiWordActivity'
        
    def matches_mime_type(cls, mime_type):
        return mime_type in cls._types
    matches_mime_type = classmethod(matches_mime_type)

class RtfFileType(FileType):
    
    _types = set(['application/rtf', 'text/rtf'])
    
    def get_name(self):
        return _('RTF file')

    def get_icon(self):
        return 'theme:activity-abiword'

    def get_preview(self):
        return ''

    def get_activity(self):
        return 'org.laptop.AbiWordActivity'
        
    def matches_mime_type(cls, mime_type):
        return mime_type in cls._types
    matches_mime_type = classmethod(matches_mime_type)

class OOTextFileType(FileType):
    
    _types = set(['application/vnd.oasis.opendocument.text'])
    
    def get_name(self):
        return _('OpenOffice text file')

    def get_icon(self):
        return 'theme:activity-abiword'

    def get_preview(self):
        return ''

    def get_activity(self):
        return 'org.laptop.AbiWordActivity'
        
    def matches_mime_type(cls, mime_type):
        return mime_type in cls._types
    matches_mime_type = classmethod(matches_mime_type)

class UnknownFileType(FileType):
    def get_name(self):
        return _('Object')

    def get_icon(self):
        return 'theme:stock-missing'

    def get_preview(self):
        return ''

    def get_activity(self):
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
        self._types.append(OOTextFileType)
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
