from gi.repository import GObject


class RemoteBackendBackup(GObject.GObject):

    __gsignals__ = {
        'started': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'progress': (GObject.SignalFlags.RUN_FIRST, None, ([float])),
        'finished': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'cancelled': (GObject.SignalFlags.RUN_FIRST, None, ([]))}

    def verify_preconditions(self):
        raise NotImplementedError()

    def start(self):
        raise NotImplementedError()

    def cancel(self):
        raise NotImplementedError()


class RemoteBackendRestore(GObject.GObject):

    __gsignals__ = {
        'started': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'progress': (GObject.SignalFlags.RUN_FIRST, None, ([float])),
        'finished': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'cancelled': (GObject.SignalFlags.RUN_FIRST, None, ([]))}

    def verify_preconditions(self):
        raise NotImplementedError()

    def start(self):
        raise NotImplementedError()

    def cancel(self):
        raise NotImplementedError()


def get_name():
    return "Remote Backup"


def get_backup():
    return RemoteBackendBackup()


def get_restore():
    return RemoteBackendRestore()
