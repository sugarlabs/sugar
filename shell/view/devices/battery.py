from view.devices import deviceview
from sugar.graphics import canvasicon

_ICON_NAME = 'device-battery'

class DeviceView(deviceview.DeviceView):
    def __init__(self, model):
        deviceview.DeviceView.__init__(self, model)

        icon_name = canvasicon.get_icon_state(_ICON_NAME, 60)
        self.props.icon_name = icon_name
