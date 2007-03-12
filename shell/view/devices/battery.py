from sugar.graphics import canvasicon

_ICON_NAME = 'device-battery'

class DeviceView(canvasicon.CanvasIcon):
    def __init__(self, model):
        canvasicon.CanvasIcon.__init__(self)
        self._model = model

        model.connect('notify::level', self._level_changed_cb)

        self._update_level()

    def _update_level(self):
        self.props.icon_name = canvasicon.get_icon_state(
                                    _ICON_NAME, self._model.props.level)

    def _level_changed_cb(self, pspec, param):
        self._update_level()
        
