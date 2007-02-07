_system_colors = {
    'toolbar-background' : '#414141'
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

class Color(object):
    RED   = Color(1.0, 0.0, 0.0)
    GREEN = Color(0.0, 1.0, 0.0)
    BLUE  = Color(0.0, 0.0, 1.0)

    def __init__(self, r, g, b, a=1.0):
        self._r = r
        self._g = g
        self._b = b

    def to_rgb(self):
        return (self._r, self._g, self._b)

class SystemColor(Color):
    TOOLBAR_BACKGROUND = SystemColor('toolbar-background')

    def __init__(self, color_id):
        rgb = _html_to_rgb(_system_colors[color_id])
        Color.__init__(*rgb)
