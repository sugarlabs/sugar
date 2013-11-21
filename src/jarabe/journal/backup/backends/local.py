from gi.repository import GObject
 
class LocalBackendBackup(GObject.GObject):
 
    __gsignals__ = {
       'started':    (GObject.SignalFlags.RUN_FIRST, None, ([])),
       'progress':   (GObject.SignalFlags.RUN_FIRST, None, ([float])),
       'finished':   (GObject.SignalFlags.RUN_FIRST, None, ([])),
       'cancelled':  (GObject.SignalFlags.RUN_FIRST, None, ([]))}
 
    def verify_preconditions(self):
        raise NotImplementedError()
 
    def start(self):
        raise NotImplementedError()
 
    def cancel(self):
        raise NotImplementedError()


class LocalBackendRestore(GObject.GObject):
 
    __gsignals__ = {
       'started':    (GObject.SignalFlags.RUN_FIRST, None, ([])),
       'progress':   (GObject.SignalFlags.RUN_FIRST, None, ([float])),
       'finished':   (GObject.SignalFlags.RUN_FIRST, None, ([])),
       'cancelled':  (GObject.SignalFlags.RUN_FIRST, None, ([]))}
 
    def verify_preconditions(self):
        raise NotImplementedError()
 
    def start(self):
        raise NotImplementedError()
 
    def cancel(self):
        raise NotImplementedError()


def get_name():
    return "Local Backup"

def get_backup():
    return LocalBackendBackup

def get_restore():
    return LocalBackendRestore
