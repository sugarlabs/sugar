import gtk

_system_colors = {
    'toolbar-background'            : '#414141',
    'frame-border'                  : '#D1D1D2',
    'entry-background-focused'      : '#FFFFFF',
    'entry-background-unfocused'    : '#D1D1D2'
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

class SystemColor(RGBColor):
    def __init__(self, color_id):
        rgb = _html_to_rgb(_system_colors[color_id])
        RGBColor.__init__(self, *rgb)

class Color(object):
    RED                = RGBColor(1.0, 0.0, 0.0)
    GREEN              = RGBColor(0.0, 1.0, 0.0)
    BLUE               = RGBColor(0.0, 0.0, 1.0)

    TOOLBAR_BACKGROUND          = SystemColor('toolbar-background')
    FRAME_BORDER                = SystemColor('frame-border')
    ENTRY_BACKGROUND_FOCUSED    = SystemColor('entry-background-focused')
    ENTRY_BACKGROUND_UNFOCUSED  = SystemColor('entry-background-unfocused')
