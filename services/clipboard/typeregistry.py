import logging
from gettext import gettext as _
import urlparse
import posixpath

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
        return 'theme:object-text'

    def get_preview(self):
        for format, data in self._formats.iteritems():
            if format in TextFileType._types:
                text = data.get_data()
                if len(text) < 50:
                    return text
                else:
                    return text[0:49] + "..."

        return ''

    def get_activity(self):
        return 'org.laptop.AbiWordActivity'
        
    def matches_mime_type(cls, mime_type):
        return mime_type in cls._types
    matches_mime_type = classmethod(matches_mime_type)

class ImageFileType(FileType):

    _types = set(['image/jpeg', 'image/gif', 'image/png', 'image/tiff'])

    def get_name(self):
        return _('Image')

    def get_icon(self):
        return 'theme:object-image'

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
        return 'theme:object-link'

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
    
    _types = set(['application/pdf', 'application/x-pdf'])
    
    def get_name(self):
        return _('PDF file')

    def get_icon(self):
        return 'theme:object-text'

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
        return 'theme:object-text'

    def get_preview(self):
        return ''

    def get_activity(self):
        return 'org.laptop.AbiWordActivity'
        
    def matches_mime_type(cls, mime_type):
        return mime_type in cls._types
    matches_mime_type = classmethod(matches_mime_type)

class RtfFileType(TextFileType):
    
    _types = set(['application/rtf', 'text/rtf'])
    
    def get_name(self):
        return _('RTF file')
        
    def matches_mime_type(cls, mime_type):
        return mime_type in cls._types
    matches_mime_type = classmethod(matches_mime_type)

class AbiwordFileType(TextFileType):
    
    _types = set(['application/x-abiword'])
    
    def get_name(self):
        return _('Abiword file')
        
    def matches_mime_type(cls, mime_type):
        return mime_type in cls._types
    matches_mime_type = classmethod(matches_mime_type)

class SqueakProjectFileType(FileType):
    
    _types = set(['application/x-squeak-project'])
    
    def get_name(self):
        return _('Squeak project')

    def get_icon(self):
        return 'theme:object-squeak-project'

    def get_preview(self):
        return ''

    def get_activity(self):
        return 'org.vpri.EtoysActivity'
        
    def matches_mime_type(cls, mime_type):
        return mime_type in cls._types
    matches_mime_type = classmethod(matches_mime_type)

class OOTextFileType(FileType):
    
    _types = set(['application/vnd.oasis.opendocument.text'])
    
    def get_name(self):
        return _('OpenOffice text file')

    def get_icon(self):
        return 'theme:object-text'

    def get_preview(self):
        return ''

    def get_activity(self):
        return 'org.laptop.AbiWordActivity'
        
    def matches_mime_type(cls, mime_type):
        return mime_type in cls._types
    matches_mime_type = classmethod(matches_mime_type)

class UriListFileType(FileType):
    
    _types = set(['text/uri-list'])

    def _is_image(self):
        uris = self._formats['text/uri-list'].get_data().split('\n')
        if len(uris) == 1:
            uri = urlparse.urlparse(uris[0])
            ext = posixpath.splitext(uri.path)[1]
            logging.debug(ext)
            # FIXME: Bad hack, the type registry should treat text/uri-list as a special case.
            if ext in ['.jpg', '.jpeg', '.gif', '.png', '.svg']:
                return True
        
        return False

    def get_name(self):
        if self._is_image():
            return _('Image')
        else:
            return _('File')

    def get_icon(self):
        if self._is_image():
            return 'theme:object-image'
        else:
            return 'theme:stock-missing'

    def get_preview(self):
        return ''

    def get_activity(self):
        return ''
        
    def matches_mime_type(cls, mime_type):
        return mime_type in cls._types
    matches_mime_type = classmethod(matches_mime_type)

class XoFileType(FileType):
    
    _types = set(['application/vnd.olpc-x-sugar'])

    def get_name(self):
        return _('Activity package')

    def get_icon(self):
        return 'theme:stock-missing'

    def get_preview(self):
        return ''

    def get_activity(self):
        return ''
        
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
        self._types.append(UriListFileType)
        self._types.append(UriFileType)
        self._types.append(ImageFileType)
        self._types.append(AbiwordFileType)
        self._types.append(TextFileType)
        self._types.append(SqueakProjectFileType)
        self._types.append(XoFileType)
    
    def get_type(self, formats):
        for file_type in self._types:
            for format, data in formats.iteritems():
                logging.debug(format)
                if file_type.matches_mime_type(format):
                    return file_type(formats)

        return UnknownFileType(formats)
    
_type_registry = None
def get_instance():
    global _type_registry
    if not _type_registry:
        _type_registry = TypeRegistry()
    return _type_registry
