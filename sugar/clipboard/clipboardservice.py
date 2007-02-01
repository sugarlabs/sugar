import logging
import dbus
import gobject

NAME_KEY = 'NAME'
PERCENT_KEY = 'PERCENT'
ICON_KEY = 'ICON'
PREVIEW_KEY = 'PREVIEW'
ACTIVITY_KEY = 'ACTIVITY'
FORMATS_KEY = 'FORMATS'

DBUS_SERVICE = "org.laptop.Clipboard"
DBUS_INTERFACE = "org.laptop.Clipboard"
DBUS_PATH = "/org/laptop/Clipboard"

class ClipboardService(gobject.GObject):

    __gsignals__ = {
        'object-added': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                        ([str, str])),
        'object-deleted': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                        ([str])),
        'object-state-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                        ([str, str, int, str, str, str])),
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
            self._connected = True

        bus.remove_signal_receiver(self._nameOwnerChangedHandler)

    def _name_owner_changed_cb(self, name, old, new):
        if not old and new:
            # ClipboardService started up
            self._connect_clipboard_signals()

    def _object_added_cb(self, object_id, name):
        self.emit('object-added', object_id, name)

    def _object_deleted_cb(self, object_id):
        self.emit('object-deleted', object_id)

    def _object_state_changed_cb(self, object_id, values):
        self.emit('object-state-changed', object_id, values[NAME_KEY],
                  values[PERCENT_KEY], values[ICON_KEY], values[PREVIEW_KEY],
                  values[ACTIVITY_KEY])

    def add_object(self, object_id, name):
        self._dbus_service.add_object(object_id, name)

    def add_object_format(self, object_id, formatType, data, on_disk):
        self._dbus_service.add_object_format(object_id,
                formatType,
                data,
                on_disk)
    
    def delete_object(self, object_id):
        self._dbus_service.delete_object(object_id)
    
    def set_object_percent(self, object_id, percent):
        self._dbus_service.set_object_percent(object_id, percent)

    def get_object(self, object_id):
        result_dict = self._dbus_service.get_object(object_id,)
        
        return (result_dict[NAME_KEY], result_dict[PERCENT_KEY],
                result_dict[ICON_KEY], result_dict[PREVIEW_KEY],
                result_dict[ACTIVITY_KEY], result_dict[FORMATS_KEY])

    def get_object_data(self, object_id, formatType):    
        return self._dbus_service.get_object_data(object_id, formatType,
                                                  byte_arrays=True)
        
_clipboard_service = None
def get_instance():
    global _clipboard_service
    if not _clipboard_service:
        _clipboard_service = ClipboardService()
    return _clipboard_service
