from sugar.graphics.canvasicon import CanvasIcon

class DeviceView(CanvasIcon):
    def __init__(self, model):
        CanvasIcon.__init__(self)
        self.model = model

def create(model):
    name = 'view.devices.' + model.get_type()

    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)

    return mod.DeviceView(model)
