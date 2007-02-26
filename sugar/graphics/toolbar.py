import gobject
import hippo

from sugar.graphics import units

class Toolbar(hippo.CanvasBox):
    __gtype_name__ = 'Toolbar'

    def __init__(self, orientation=hippo.ORIENTATION_HORIZONTAL):
        hippo.CanvasBox.__init__(self, orientation=orientation,
                                 background_color=0x414141ff,
                                 box_height=units.grid_to_pixels(1),
                                 spacing=units.points_to_pixels(5)
)
