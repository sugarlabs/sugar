import gobject

from model.devices import device

class Device(device.Device):
    __gproperties__ = {
        'level' : (int, None, None, 0, 100, 0,
                   gobject.PARAM_READABLE)
    }

    def __init__(self):
        device.Device.__init__(self)
        
        self._level = 0
        self._timeout_id = gobject.timeout_add(2000, self._check_battery_level)

    def do_get_property(self, pspec):
        if pspec.name == 'level':
            return self._level 

    def get_type(self):
        return 'battery'

    def _check_battery_level(self):
        new_level = self._get_battery_level()
        
        if new_level != self._level:
            self._level = new_level
            self.notify('level')

        return True

    def _get_battery_level(self):
        battery_class_path = '/sys/class/battery/psu_0/'

        capacity_path = battery_class_path + 'capacity_percentage'
        try:
            f = open(capacity_path, 'r')
            val = f.read().split('\n')
            level = int(val[0])
            f.close()
        except:
            level = 0

        return level

    def __del__(self):
        gobject.source_remove(self._timeout_id)
        self._timeout_id = 0
