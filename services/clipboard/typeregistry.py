import logging
from gettext import gettext as _
import urlparse
import posixpath

class FileType:
    """Generic base class for all classes representing clipboard item formats.

    XXX This class's name is misleading; it represents a clipboard item
    format and not a file type per se.  Perhaps it should be renamed to
    ClipboardItemFormat?
    """
    
    def __init__(self, formats):
        """Initializer for this class (and all subclasses).
        
        formats -- A dictionary of key-value pairs where the keys are MIME type
            strings and the data values are the clipboard data in each
            respective format.  A reference to this dictionary is stored within
            the object for possible use later.
        
        This initializer is invoked when the clipboard item format object is
        instantiated by the TypeRegistry class's get_type method.
        
        """
        self._formats = formats

    def get_name(self):
        """Returns a localized human-readable name for this clipboard item format.
        
        This base-class implementation raises a NotImplementedError exception.
        
        returns A localized string containing the clipboard item format name.
        """
        raise NotImplementedError

    def get_icon(self):
        """XXX Returns a "tag" to be used to get an icon for this clipboard item format (I think).
        
        This base-class implementation raises a NotImplementedError exception.
        
        returns XXX A string "tag" to be used to get the icon for this clipboard
            item format (I think).
        """
        raise NotImplementedError

    def get_preview(self):
        """Returns an appropriate preview of the clipboard item data for this item format.
        
        This base-class implementation raises a NotImplementedError exception.
        
        returns A string containing the item preview.
        """
        raise NotImplementedError

    def get_activity(self):
        """Returns the activity identifier associated with this clipboard item format.
        
        This base-class implementation raises a NotImplementedError exception.
        
        returns A string containing the activity identifier. 
        """
        raise NotImplementedError
        
    def matches_mime_type(cls, mime_type):
        """Class method to determine whether this class handles a given MIME type.
        
        mime_type -- A string containing the MIME type.
        
        XXX This base-class implementation currently raises a
        NotImplementedError exception, but could (and should) be rewritten to
        handle this functionality for *all* subclasses, since the code is
        identical for all or most subclasses anyway.
       
        returns True if this class handles the given MIME type, False otherwise.
        """
        raise NotImplementedError
        
    matches_mime_type = classmethod(matches_mime_type)

    
class TextFileType(FileType):
    """Represents the text clipboard item format.
    
    XXX This class's name is misleading; it represents a clipboard item format
    and not a file type per se.
    """

    _types = set(['text/plain', 'UTF8_STRING', 'STRING'])

    def get_name(self):
        """Returns a localized human-readable name for this clipboard item format.
        
        returns A localized string containing the clipboard item format name.
        """
        return _('Text snippet')

    def get_icon(self):
        """XXX Returns a "tag" to be used to get an icon for this clipboard item format (I think).
        
        returns XXX A string "tag" to be used to get the icon for this clipboard
            item format (I think).
        """
        return 'theme:object-text'

    def get_preview(self):
        """Returns an appropriate preview of the clipboard item data for this item format.
        
        For the text file format, this returns a text string containing up to
        49 characters of the actual item's text.
        
        returns A preview string containing up to 49 characters of the item's
            text.
        """
        for format, data in self._formats.iteritems():
            if format in TextFileType._types:
                text = data.get_data()
                if len(text) < 50:
                    return text
                else:
                    return text[0:49] + "..."

        return ''

    def get_activity(self):
        """Returns the activity identifier associated with this clipboard item format.
        
        returns A string containing the activity identifier. 
        """
        return 'org.laptop.AbiWordActivity'
        
    def matches_mime_type(cls, mime_type):
        """Class method to determine whether this class handles a given MIME type.
        
        mime_type -- A string containing the MIME type.
        
        XXX This subclass method is unnecessary; a single base class method
        in the FileType class would be sufficient to handle all or most
        subclasses, since the code is identical for all or most subclasses
        anyway.
        
        returns True if this class handles the given MIME type, False otherwise.
        """
        return mime_type in cls._types
        
    matches_mime_type = classmethod(matches_mime_type)

    
class ImageFileType(FileType):
    """Represents the "image" clipboard item format.
    
    This clipboard item format represents *any* image format, including JPEG,
    GIF, PNG and TIFF formats.
    
    XXX This class's name is misleading; it represents a clipboard item format
    and not a file type per se.
    """

    _types = set(['image/jpeg', 'image/gif', 'image/png', 'image/tiff'])

    def get_name(self):
        """Returns a localized human-readable name for this clipboard item format.
        
        returns A localized string containing the clipboard item format name.
        """
        return _('Image')

    def get_icon(self):
        """XXX Returns a "tag" to be used to get an icon for this clipboard item format (I think).
        
        returns XXX A string "tag" to be used to get the icon for this clipboard
            item format (I think).
        """
        return 'theme:object-image'

    def get_preview(self):
        """Returns an appropriate preview of the clipboard item data for this item format.
        
        XXX Currently returns an empty string.
        
        returns A string containing the item preview.
        """
        return ''

    def get_activity(self):
        """Returns the activity identifier associated with this clipboard item format.
        
        returns A string containing the activity identifier. 
        """
        return ''
        
    def matches_mime_type(cls, mime_type):
        """Class method to determine whether this class handles a given MIME type.
        
        mime_type -- A string containing the MIME type.
        
        XXX This subclass method is unnecessary; a single base class method
        in the FileType class would be sufficient to handle all or most
        subclasses, since the code is identical for all or most subclasses
        anyway.
        
        returns True if this class handles the given MIME type, False otherwise.
        """
        return mime_type in cls._types
        
    matches_mime_type = classmethod(matches_mime_type)

    
class UriFileType(FileType):
    """Represents the URI clipboard item format.
    
    Not to be confused with the multiple-URI UriListFileType class.
    
    XXX This class's name is misleading; it represents a clipboard item format
    and not a file type per se.
    """
    
    _types = set(['_NETSCAPE_URL'])
    
    def get_name(self):
        """Returns a localized human-readable name for this clipboard item format.
        
        returns A localized string containing the clipboard item format name.
        """
        return _('Web Page')

    def get_icon(self):
        """XXX Returns a "tag" to be used to get an icon for this clipboard item format (I think).
        
        returns XXX A string "tag" to be used to get the icon for this clipboard
            item format (I think).
        """
        return 'theme:object-link'

    def get_preview(self):
        """Returns an appropriate preview of the clipboard item data for this item format.
        
        For the URI clipboard item format, this is the URI itself.
        
        returns A string containing the item preview, in this case the URI itself.
        """
        for format, data in self._formats.iteritems():
            if format in UriFileType._types:
                string = data.get_data()
                title = string.split("\n")[1]
                return title
        
        return ''

    def get_activity(self):
        """Returns the activity identifier associated with this clipboard item format.
        
        returns A string containing the activity identifier. 
        """
        return ''

    def matches_mime_type(cls, mime_type):
        """Class method to determine whether this class handles a given MIME type.
        
        mime_type -- A string containing the MIME type.
        
        XXX This subclass method is unnecessary; a single base class method
        in the FileType class would be sufficient to handle all or most
        subclasses, since the code is identical for all or most subclasses
        anyway.
        
        returns True if this class handles the given MIME type, False otherwise.
        """
        return mime_type in cls._types
        
    matches_mime_type = classmethod(matches_mime_type)

    
class PdfFileType(FileType):
    """Represents the PDF clipboard item format.
    
    XXX This class's name is misleading; it represents a clipboard item format
    and not a file type per se.
    """
    
    _types = set(['application/pdf', 'application/x-pdf'])
    
    def get_name(self):
        """Returns a localized human-readable name for this clipboard item format.
        
        returns A localized string containing the clipboard item format name.
        """
        return _('PDF file')

    def get_icon(self):
        """XXX Returns a "tag" to be used to get an icon for this clipboard item format (I think).
        
        returns XXX A string "tag" to be used to get the icon for this clipboard
            item format (I think).
        """
        return 'theme:object-text'

    def get_preview(self):
        """Returns an appropriate preview of the clipboard item data for this item format.
        
        XXX Currently returns an empty string.
        
        returns A string containing the item preview.
        """
        return ''

    def get_activity(self):
        """Returns the activity identifier associated with this clipboard item format.
        
        returns A string containing the activity identifier. 
        """
        return 'org.laptop.sugar.Xbook'
        
    def matches_mime_type(cls, mime_type):
        """Class method to determine whether this class handles a given MIME type.
        
        mime_type -- A string containing the MIME type.
        
        XXX This subclass method is unnecessary; a single base class method
        in the FileType class would be sufficient to handle all or most
        subclasses, since the code is identical for all or most subclasses
        anyway.
        
        returns True if this class handles the given MIME type, False otherwise.
        """
        return mime_type in cls._types
        
    matches_mime_type = classmethod(matches_mime_type)

    
class MsWordFileType(FileType):
    """Represents the MS Word clipboard item format (*cringe*).
    
    XXX This class's name is misleading; it represents a clipboard item format
    and not a file type per se.
    """
    
    _types = set(['application/msword'])
    
    def get_name(self):
        """Returns a localized human-readable name for this clipboard item format.
        
        returns A localized string containing the clipboard item format name.
        """
        return _('MS Word file')

    def get_icon(self):
        """XXX Returns a "tag" to be used to get an icon for this clipboard item format (I think).
        
        returns XXX A string "tag" to be used to get the icon for this clipboard
            item format (I think).
        """
        return 'theme:object-text'

    def get_preview(self):
        """Returns an appropriate preview of the clipboard item data for this item format.
        
        XXX Currently returns an empty string.
        
        returns A string containing the item preview.
        """
        return ''

    def get_activity(self):
        """Returns the activity identifier associated with this clipboard item format.
        
        returns A string containing the activity identifier. 
        """
        return 'org.laptop.AbiWordActivity'
        
    def matches_mime_type(cls, mime_type):
        """Class method to determine whether this class handles a given MIME type.
        
        mime_type -- A string containing the MIME type.
        
        XXX This subclass method is unnecessary; a single base class method
        in the FileType class would be sufficient to handle all or most
        subclasses, since the code is identical for all or most subclasses
        anyway.
       
        returns True if this class handles the given MIME type, False otherwise.
        """
        return mime_type in cls._types
        
    matches_mime_type = classmethod(matches_mime_type)

    
class RtfFileType(TextFileType):
    """Represents the RTF clipboard item format (a subclass of TextFileType).
    
    XXX This class's name is misleading; it represents a clipboard item format
    and not a file type per se.
    """
    
    _types = set(['application/rtf', 'text/rtf'])
    
    def get_name(self):
        """Returns a localized human-readable name for this clipboard item format.
        
        returns A localized string containing the clipboard item format name.
        """
        return _('RTF file')
        
    def matches_mime_type(cls, mime_type):
        """Class method to determine whether this class handles a given MIME type.
        
        mime_type -- A string containing the MIME type.
        
        XXX This subclass method is unnecessary; a single base class method
        in the FileType class would be sufficient to handle all or most
        subclasses, since the code is identical for all or most subclasses
        anyway.
        
        returns True if this class handles the given MIME type, False otherwise.
        """
        return mime_type in cls._types
        
    matches_mime_type = classmethod(matches_mime_type)

    
class AbiwordFileType(TextFileType):
    """Represents the AbiWord clipboard item format.
   
    (XXX This class's name is misleading; it represents a clipboard item format,
    not a file type per se.)
    (XXX AbiWord format is a full word processing format, like the OO Text and MS Word
    formats, and should not be a subclass of TextFileType!  Otherwise the OO Text and
    MS Word format types should also be made subclasses of TextFileType.)
    """
    
    _types = set(['application/x-abiword'])
    
    def get_name(self):
        """Returns a localized human-readable name for this clipboard item format.
        
        returns A localized string containing the clipboard item format name.
        """
        return _('Abiword file')
        
    def matches_mime_type(cls, mime_type):
        """Class method to determine whether this class handles a given MIME type.
        
        mime_type -- A string containing the MIME type.
        
        XXX This subclass method is unnecessary; a single base class method
        in the FileType class would be sufficient to handle all or most
        subclasses, since the code is identical for all or most subclasses
        anyway.
        
        returns True if this class handles the given MIME type, False otherwise.
        """
        return mime_type in cls._types
        
    matches_mime_type = classmethod(matches_mime_type)

    
class SqueakProjectFileType(FileType):
    """Represents the Squeak Project clipboard item format.
    
    XXX This class's name is misleading; it represents a clipboard item format
    and not a file type per se.
    """
    
    _types = set(['application/x-squeak-project'])
    
    def get_name(self):
        """Returns a localized human-readable name for this clipboard item format.
        
        returns A localized string containing the clipboard item format name.
        """
        return _('Squeak project')

    def get_icon(self):
        """XXX Returns a "tag" to be used to get an icon for this clipboard item format (I think).
        
        returns XXX A string "tag" to be used to get the icon for this clipboard
            item format (I think).
        """
        return 'theme:object-squeak-project'

    def get_preview(self):
        """Returns an appropriate preview of the clipboard item data for this item format.
        
        XXX Currently returns an empty string.
        
        returns A string containing the item preview.
        """
        return ''

    def get_activity(self):
        """Returns the activity identifier associated with this clipboard item format.
        
        returns A string containing the activity identifier. 
        """
        return 'org.vpri.EtoysActivity'
        
    def matches_mime_type(cls, mime_type):
        """Class method to determine whether this class handles a given MIME type.
        
        mime_type -- A string containing the MIME type.
        
        XXX This subclass method is unnecessary; a single base class method
        in the FileType class would be sufficient to handle all or most
        subclasses, since the code is identical for all or most subclasses
        anyway.
        
        returns True if this class handles the given MIME type, False otherwise.
        """
        return mime_type in cls._types
        
    matches_mime_type = classmethod(matches_mime_type)

    
class OOTextFileType(FileType):
    """Represents the OpenDocument Text (OpenOffice.org Writer) clipboard item format.
    
    Note to the uninitiated: OpenDocument Text is a full word processing format,
    not a simple text file.
    
    XXX This class's name is misleading; it represents a clipboard item format
    and not a file type per se.
    """
    
    _types = set(['application/vnd.oasis.opendocument.text'])
    
    def get_name(self):
        """Returns a localized human-readable name for this clipboard item format.
        
        returns A localized string containing the clipboard item format name.
        """
        return _('OpenOffice text file')

    def get_icon(self):
        """XXX Returns a "tag" to be used to get an icon for this clipboard item format (I think).
        
        returns XXX A string "tag" to be used to get the icon for this clipboard
            item format (I think).
        """
        return 'theme:object-text'

    def get_preview(self):
        """Returns an appropriate preview of the clipboard item data for this item format.
        
        XXX Currently returns an empty string.
        
        returns A string containing the item preview.
        """
        return ''

    def get_activity(self):
        """Returns the activity identifier associated with this clipboard item format.
        
        returns A string containing the activity identifier. 
        """
        return 'org.laptop.AbiWordActivity'
        
    def matches_mime_type(cls, mime_type):
        """Class method to determine whether this class handles a given MIME type.
        
        mime_type -- A string containing the MIME type.
        
        XXX This subclass method is unnecessary; a single base class method
        in the FileType class would be sufficient to handle all or most
        subclasses, since the code is identical for all or most subclasses
        anyway.
        
        returns True if this class handles the given MIME type, False otherwise.
        """
        return mime_type in cls._types
        
    matches_mime_type = classmethod(matches_mime_type)

    
class UriListFileType(FileType):
    """Represents the URI-list clipboard item format.
   
    Not to be confused with the single-URI UriFileType class.
    
    XXX This class's name is misleading; it represents a clipboard item format
    and not a file type per se.
    """
    
    _types = set(['text/uri-list'])

    def _is_image(self):
        """Determines whether this URI list represents an image.
        
        Called by the get_name and get_icon methods.  For this URI list to be
        considered to represent an image, it must fulfil two criteria: (1) it
        must have only one URI in it, and (2) the URI must end with an extension
        indicating an image type (currently ".jpg", ".jpeg", ".gif", ".png", or
        ".svg").
        
        returns True if there is one URI in the list and it represents an image,
            False otherwise.
        """
        uris = self._formats['text/uri-list'].get_data().split('\n')
        if len(uris) == 1:
            uri = urlparse.urlparse(uris[0])
            ext = posixpath.splitext(uri[2])[1]
            logging.debug(ext)
            # FIXME: Bad hack, the type registry should treat text/uri-list as a special case.
            if ext in ['.jpg', '.jpeg', '.gif', '.png', '.svg']:
                return True
        
        return False

    def get_name(self):
        """Returns a localized human-readable name for this clipboard item format.
        
        returns A localized string containing the clipboard item format name.
        """
        if self._is_image():
            return _('Image')
        else:
            return _('File')

    def get_icon(self):
        """XXX Returns a "tag" to be used to get an icon for this clipboard item format (I think).
        
        returns XXX A string "tag" to be used to get the icon for this clipboard
            item format (I think).
        """
        if self._is_image():
            return 'theme:object-image'
        else:
            return 'theme:stock-missing'

    def get_preview(self):
        """Returns an appropriate preview of the clipboard item data for this item format.
        
        XXX Currently returns an empty string.
        
        returns A string containing the item preview.
        """
        return ''

    def get_activity(self):
        """Returns the activity identifier associated with this clipboard item format.
        
        returns A string containing the activity identifier. 
        """
        return ''
        
    def matches_mime_type(cls, mime_type):
        """Class method to determine whether this class handles a given MIME type.
        
        mime_type -- A string containing the MIME type.
        
        XXX This subclass method is unnecessary; a single base class method
        in the FileType class would be sufficient to handle all or most
        subclasses, since the code is identical for all or most subclasses
        anyway.
        
        returns True if this class handles the given MIME type, False otherwise.
        """
        return mime_type in cls._types
        
    matches_mime_type = classmethod(matches_mime_type)

    
class XoFileType(FileType):
    """Represents the "xo" (OLPC package) clipboard item format.
    
    XXX This class's name is misleading; it represents a clipboard item format
    and not a file type per se.
    """
    
    _types = set(['application/vnd.olpc-x-sugar'])

    def get_name(self):
        """Returns a localized human-readable name for this clipboard item format.
        
        returns A localized string containing the clipboard item format name.
        """
        return _('Activity package')

    def get_icon(self):
        """XXX Returns a "tag" to be used to get an icon for this clipboard item format (I think).
        
        returns XXX A string "tag" to be used to get the icon for this clipboard
            item format (I think).
        """
        return 'theme:stock-missing'

    def get_preview(self):
        """Returns an appropriate preview of the clipboard item data for this item format.
        
        XXX Currently returns an empty string.
        
        returns A string containing the item preview.
        """
        return ''

    def get_activity(self):
        """Returns the activity identifier associated with this clipboard item format.
        
        returns A string containing the activity identifier. 
        """
        return ''
        
    def matches_mime_type(cls, mime_type):
        """Class method to determine whether this class handles a given MIME type.
        
        mime_type -- A string containing the MIME type.
        
        XXX This subclass method is unnecessary; a single base class method
        in the FileType class would be sufficient to handle all or most
        subclasses, since the code is identical for all or most subclasses
        anyway.
        
        returns True if this class handles the given MIME type, False otherwise.
        """
        return mime_type in cls._types
        
    matches_mime_type = classmethod(matches_mime_type)

    
class UnknownFileType(FileType):
    """Represents an unknown clipboard item format.
    
    XXX This class's name is misleading; it represents a clipboard item format
    and not a file type per se.
    """
    def get_name(self):
        """Returns a localized human-readable name for this clipboard item format.
        
        Since this clipboard item format is unknown, the format name will be
        simply "Object" or something to that effect.
        
        returns A localized string containing the clipboard item format name.
        """
        return _('Object')

    def get_icon(self):
        """XXX Returns a "tag" to be used to get an icon for this clipboard item format (I think).
        
        returns XXX A string "tag" to be used to get the icon for this clipboard
            item format (I think).
        """
        return 'theme:stock-missing'

    def get_preview(self):
        """Returns a "preview" for this clipboard item format.
        
        Since this clipboard item format is unknown, there can be no preview for
        it, so the "preview" will be an empty string.
        
        returns An empty string, since there can be no preview for an unknown
            clipboard item format.
        """
        return ''

    def get_activity(self):
        """Returns the activity identifier associated with this clipboard item format.
        
        Since this clipboard item format is unknown, there can be no activity
        associated with it, so the activity identifier will be an empty string.
        
        returns A string containing the activity identifier (an empty string in
            this case).
        """
        return ''
        
    def matches_mime_type(cls, mime_type):
        """Class method to determine whether this class handles a given MIME type.
        
        mime_type -- A string containing the MIME type.
        
        Always returns true, since UnknownFileType is the clipboard item format
        class of last resort and must be used if no other class handles the
        given MIME type.
        
        returns True if this class handles the given MIME type (always true in
            this case).
        """
        return true
        
    matches_mime_type = classmethod(matches_mime_type)

    
class TypeRegistry:
    """Represents a registry of all clipboard item formats.
    
    There will be one single global instantiation of this object, accessible via
    the global typeregistry.get_instance method.
    """
    def __init__(self):
        """Initializes the registry.
        """
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
        """Returns a matching clipboard item format object for the passed-in clipboard data.
        
        formats -- A dictionary of key-value pairs where the keys are MIME type
            strings and the data values are the clipboard data in each
            respective format.
        
        A reference to the given clipboard data format dictionary is stored
        within the returned object for possible use later.
        
        XXX The order of the clipboard item formats in the TypeRegistry object's
        internal list matters.  For example, if clipboard item data is available
        in both MS Word and OO Text formats, the MS Word type will currently be
        matched first, and therefore an MsWordFileType object will be returned.
        Is this really what is desired?  The ordering should definitely be given
        some thought.
        
        returns A clipboard item format object of a type matching one of the
            MIME type keys in the formats dictionary, or an UnknownFileType
            object if none of the other types is appropriate.
        """
        for file_type in self._types:
            for format, data in formats.iteritems():
                if file_type.matches_mime_type(format):
                    return file_type(formats)

        return UnknownFileType(formats)
    
_type_registry = None
def get_instance():
    """Returns the global clipboard item format registry object (global method).
    
    Returns a reference to the global clipboard item format registry object,
    instantiating it first if necessary.
    
    returns A TypeRegistry object representing the global clipboard item format
        registry.
    """
    global _type_registry
    if not _type_registry:
        _type_registry = TypeRegistry()
    return _type_registry
