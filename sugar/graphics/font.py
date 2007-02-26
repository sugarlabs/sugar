import pango

from sugar.graphics import units

_system_fonts = {
    'default'       : 'Bitstream Vera Sans %d' % units.points_to_pixels(9),
    'default-bold'  : 'Bitstream Vera Sans bold %d' % units.points_to_pixels(9)
}

class Font(object):
    def __init__(self, desc):
        self._desc = desc

    def get_desc(self):
        return self._desc

    def get_pango_desc(self):
        return pango.FontDescription(self._desc)

class SystemFont(Font):
    def __init__(self, font_id):
        Font.__init__(self, _system_fonts[font_id])

DEFAULT = SystemFont('default')
DEFAULT_BOLD = SystemFont('default-bold')
