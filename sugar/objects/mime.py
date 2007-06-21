try:
    from sugar import _sugarext
except ImportError:
    from sugar import ltihooks
    from sugar import _sugarext

def get_for_file(file_name):
    return _sugarext.get_mime_type_for_file(file_name)
        
def get_from_file_name(file_name):
    return _sugarext.get_mime_type_from_file_name(file_name)

_extensions_cache = {}
def get_primary_extension(mime_type):
    if _extensions_cache.has_key(mime_type):
        return _extensions_cache[mime_type]

    f = open('/etc/mime.types')
    while True:
        line = f.readline()
        cols = line.replace('\t', ' ').split(' ')
        if mime_type == cols[0]:
            for col in cols[1:]:
                if col:
                    _extensions_cache[mime_type] = col
                    return col

    _extensions_cache[mime_type] = None
    return None
