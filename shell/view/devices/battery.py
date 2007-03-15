from sugar.graphics import canvasicon
from sugar.graphics import units

_ICON_NAME = 'device-battery'

class DeviceView(canvasicon.CanvasIcon):
    def __init__(self, model):
        canvasicon.CanvasIcon.__init__(self, scale=units.MEDIUM_ICON_SCALE)
        self._model = model

        model.connect('notify::level', self._level_changed_cb)

        self._update_level()

    def _update_level(self):
        self.props.icon_name = canvasicon.get_icon_state(
                                    _ICON_NAME, self._model.props.level)

    def _level_changed_cb(self, pspec, param):
        self._update_level()
        
