import hippo

from sugar.graphics import style
from sugar.graphics.canvasicon import CanvasIcon

class OverlayBox(hippo.CanvasBox):
    def __init__(self, shell):
        hippo.CanvasBox.__init__(self, orientation=hippo.ORIENTATION_HORIZONTAL)

        self._shell = shell

        icon = CanvasIcon(icon_name='theme:stock-chat')
        style.apply_stylesheet(icon, 'frame.OverlayIcon')
        icon.connect('activated', self._overlay_clicked_cb)
        self.append(icon)

    def _overlay_clicked_cb(self, item):
        self._shell.toggle_chat_visibility()
