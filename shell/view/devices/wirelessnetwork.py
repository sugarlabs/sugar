from view.devices import deviceview

class DeviceView(deviceview.DeviceView):
    def __init__(self, model):
        deviceview.DeviceView.__init__(self, model)
        self._model = model

        self._update_icon()
        model.connect('notify::strength', self._strength_changed_cb)

    def _strength_changed_cb(self, model, pspec):
        self._update_icon()

    def _update_icon(self):
        strength = self._model.props.strength
        if strength < 21:
            self.props.icon_name = 'theme:stock-net-wireless-00'
        elif strength < 41:
            self.props.icon_name = 'theme:stock-net-wireless-21-40'
        elif strength < 61:
            self.props.icon_name = 'theme:stock-net-wireless-41-60'
        elif strength < 81:
            self.props.icon_name = 'theme:stock-net-wireless-61-80'
        else:
            self.props.icon_name = 'theme:stock-net-wireless-81-100'
