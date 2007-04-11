import logging
import dbus
import gobject

NAME_KEY = 'NAME'
PERCENT_KEY = 'PERCENT'
FORMATS_KEY = 'FORMATS'

DBUS_SERVICE = "org.laptop.Clipboard"
DBUS_INTERFACE = "org.laptop.Clipboard"
DBUS_PATH = "/org/laptop/Clipboard"

class ClipboardService(gobject.GObject):
    __gsignals__ = {
        'object-added':   (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                           ([str, str])),
        'object-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                           ([str, str, gobject.TYPE_PYOBJECT])),
        'object-deleted': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                           ([str])),
        'object-state-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                                 ([str, int])),
    }
    
    def __init__(self):
        gobject.GObject.__init__(self)

        self._dbus_service = None

        bus = dbus.SessionBus()
        self._nameOwnerChangedHandler = bus.add_signal_receiver(
                self._name_owner_changed_cb,
                signal_name="NameOwnerChanged",
                dbus_interface="org.freedesktop.DBus",
                arg0=DBUS_SERVICE)

        self._connected = False
        # Try to register to ClipboardService, if we fail, we'll try later.
        try:
            self._connect_clipboard_signals()
        except dbus.DBusException, exception:
            logging.debug(exception)

    def _connect_clipboard_signals(self):
        bus = dbus.SessionBus()
        if not self._connected:
            proxy_obj = bus.get_object(DBUS_SERVICE, DBUS_PATH)
            self._dbus_service = dbus.Interface(proxy_obj, DBUS_SERVICE)
            self._dbus_service.connect_to_signal('object_added',
                                                 self._object_added_cb)
            self._dbus_service.connect_to_signal('object_deleted',
                                                 self._object_deleted_cb)
            self._dbus_service.connect_to_signal('object_state_changed',
                                                 self._object_state_changed_cb)
            self._dbus_service.connect_to_signal('object_changed',
                                                 self._object_changed_cb)
            self._connected = True

        bus.remove_signal_receiver(self._nameOwnerChangedHandler)

    def _name_owner_changed_cb(self, name, old, new):
        if not old and new:
            # ClipboardService started up
            self._connect_clipboard_signals()

    def _object_added_cb(self, object_id, name):
        self.emit('object-added', str(object_id), name)

    def _object_changed_cb(self, object_id, values):
        self.emit('object-changed', str(object_id),
                  values[NAME_KEY], values[FORMATS_KEY])

    def _object_deleted_cb(self, object_id):
        self.emit('object-deleted', str(object_id))

    def _object_state_changed_cb(self, object_id, values):
        self.emit('object-state-changed', str(object_id), values[PERCENT_KEY])

    def add_object(self, name):
        return str(self._dbus_service.add_object(name))

    def add_object_format(self, object_id, formatType, data, on_disk):
        self._dbus_service.add_object_format(dbus.ObjectPath(object_id),
                formatType,
                data,
                on_disk)
    
    def delete_object(self, object_id):
        self._dbus_service.delete_object(dbus.ObjectPath(object_id))
    
    def set_object_percent(self, object_id, percent):
        self._dbus_service.set_object_percent(dbus.ObjectPath(object_id), percent)

    def get_object(self, object_id):
        return self._dbus_service.get_object(dbus.ObjectPath(object_id),)

    def get_object_data(self, object_id, formatType):    
        return self._dbus_service.get_object_data(dbus.ObjectPath(object_id),
                                                  formatType,
                                                  byte_arrays=True)
        
_clipboard_service = None
def get_instance():
    global _clipboard_service
    if not _clipboard_service:
        _clipboard_service = ClipboardService()
    return _clipboard_service
