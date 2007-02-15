import gobject
import hippo

class Toolbar(hippo.CanvasBox):
    __gtype_name__ = 'Toolbar'

    def __init__(self, orientation=hippo.ORIENTATION_HORIZONTAL):
        hippo.CanvasBox.__init__(self, orientation=orientation,
                                 background_color=0x414141ff,
                                 spacing=15)
