try:
    from sugar import _sugarext
except ImportError:
    from sugar import ltihooks
    from sugar import _sugarext

def get_for_file(file_name):
    return _sugarext.get_mime_type_for_file(file_name)
        
def get_from_file_name(file_name):
    return _sugarext.get_mime_type_from_file_name(file_name)
