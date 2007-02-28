from sugar.graphics import canvasicon

_ICON_NAME = 'device-battery'

class DeviceView(canvasicon.CanvasIcon):
    def __init__(self, model):
        canvasicon.CanvasIcon.__init__(self)
        self._model = model

        icon_name = canvasicon.get_icon_state(_ICON_NAME, 60)
        self.props.icon_name = icon_name
