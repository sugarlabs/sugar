from view.devices import deviceview

class DeviceView(deviceview.DeviceView):
    def __init__(self, model):
        deviceview.DeviceView.__init__(self, model)
        self.props.icon_name = 'theme:stock-net-wired'
