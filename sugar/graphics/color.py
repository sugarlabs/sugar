import gtk

_system_colors = {
    'toolbar-background'            : '#414141',
    'frame-border'                  : '#D1D1D2',
    'entry-background-focused'      : '#FFFFFF',
    'entry-background-unfocused'    : '#414141',
    'entry-selection-focused'       : '#D1D1D2',
    'entry-selection-unfocused'     : '#00FF00',
    'entry-text-focused'            : '#000000',
    'entry-text-unfocused'          : '#FFFFFF',
    'entry-border'                  : '#D1D1D2',
    'label-text'                    : '#FFFFFF',
    'desktop-background'            : '#E2E2E3',
    'menu-background'               : '#000000',
    'menu-separator'                : '#D1D1D2',
    'menu-border'                   : '#D1D1D2',
    'button-normal'                 : '#FFFFFF',
    'button-background-normal'      : '#424242',
    'button-hover'                  : '#808080',
    'button-background-hover'       : '#000000',
    'button-inactive'               : '#808080',
    'button-background-inactive'    : '#424242'
}

def _html_to_rgb(html_color):
    """ #RRGGBB -> (r, g, b) tuple (in float format) """

    html_color = html_color.strip()
    if html_color[0] == '#':
        html_color = html_color[1:]
    if len(html_color) != 6:
        raise ValueError, "input #%s is not in #RRGGBB format" % html_color

    r, g, b = html_color[:2], html_color[2:4], html_color[4:]
    r, g, b = [int(n, 16) for n in (r, g, b)]
    r, g, b = (r / 255.0, g / 255.0, b / 255.0)

    return (r, g, b)

def _rgba_to_int(r, g, b, a):
    color = int(a * 255) + (int(b * 255) << 8) + \
            (int(g * 255) << 16) + (int(r * 255) << 24)
    return color

class RGBColor(object):
    def __init__(self, r, g, b, a=1.0):
        self._r = r
        self._g = g
        self._b = b
        self._a = a

    def get_rgba(self):
        return (self._r, self._g, self._b, self._a)

    def get_int(self):
        return _rgba_to_int(self._r, self._g, self._b, self._a)

    def get_gdk_color(self):
        return gtk.gdk.Color(int(self._r * 65535), int(self._g * 65535),
                             int(self._b * 65535))

    def get_html(self):
        return '#%x%x%x' % (self._r * 255, self._g * 255, self._b * 255)

class HTMLColor(RGBColor):
    def __init__(self, html_color):
        rgb = _html_to_rgb(html_color)
        RGBColor.__init__(self, *rgb)

class SystemColor(HTMLColor):
    def __init__(self, color_id):
        HTMLColor.__init__(self, _system_colors[color_id])

RED   = RGBColor(1.0, 0.0, 0.0)
GREEN = RGBColor(0.0, 1.0, 0.0)
BLUE  = RGBColor(0.0, 0.0, 1.0)
WHITE = RGBColor(1.0, 1.0, 1.0)
BLACK = RGBColor(0.0, 0.0, 0.0)

TOOLBAR_BACKGROUND          = SystemColor('toolbar-background')
FRAME_BORDER                = SystemColor('frame-border')
ENTRY_BACKGROUND_FOCUSED    = SystemColor('entry-background-focused')
ENTRY_BACKGROUND_UNFOCUSED  = SystemColor('entry-background-unfocused')
ENTRY_SELECTION_FOCUSED     = SystemColor('entry-selection-focused')
ENTRY_SELECTION_UNFOCUSED   = SystemColor('entry-selection-unfocused')
ENTRY_TEXT_FOCUSED          = SystemColor('entry-text-focused')
ENTRY_TEXT_UNFOCUSED        = SystemColor('entry-text-unfocused')
ENTRY_BORDER                = SystemColor('entry-border')
LABEL_TEXT                  = SystemColor('label-text')
DESKTOP_BACKGROUND          = SystemColor('desktop-background')
MENU_BACKGROUND             = SystemColor('menu-background')
MENU_SEPARATOR              = SystemColor('menu-separator')
MENU_BORDER                 = SystemColor('menu-border')
BUTTON_NORMAL               = SystemColor('button-normal')
BUTTON_BACKGROUND_NORMAL    = SystemColor('button-background-normal')
BUTTON_HOVER                = SystemColor('button-hover')
BUTTON_BACKGROUND_HOVER     = SystemColor('button-background-hover')
BUTTON_INACTIVE             = SystemColor('button-inactive')
BUTTON_BACKGROUND_INACTIVE  = SystemColor('button-background-inactive')
