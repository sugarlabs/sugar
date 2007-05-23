from sugar import _sugarext

def get_from_filename(filename):
    return _sugarext.get_mime_type_from_filename(filename)
