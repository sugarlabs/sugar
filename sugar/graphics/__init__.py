"""Graphics/controls for use in Sugar"""
try:
    from sugar._sugarext import AddressEntry
except ImportError:
    from sugar import ltihooks
    from sugar._sugarext import AddressEntry

