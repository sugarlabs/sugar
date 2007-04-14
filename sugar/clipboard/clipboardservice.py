"""UI class to access system-level clipboard object"""
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
    """GUI interfaces for the system clipboard dbus service
    
    This object is used to provide convenient access to the clipboard
    service (see source/services/clipboard/clipboardservice.py).  It 
    provides utility methods for adding/getting/removing objects from 
    the clipboard as well as generating events when such events occur.
    
    Meaning is source/services/clipboard/clipboardobject.py 
    objects when describing "objects" on the clipboard.
    """
    __gsignals__ = {
        'object-added': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                        ([str, str])),
        'object-deleted': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                        ([str])),
        'object-state-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                        ([str, str, int, str, str, str])),
    }
    
    def __init__(self):
        """Initialise the ClipboardService instance
        
        If the service is not yet active in the background uses 
        a signal watcher to connect when the service appears.
        """
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
        """Connect dbus signals to our GObject signal generating callbacks"""
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
        """On backend service creation, connect to the server"""
        if not old and new:
            # ClipboardService started up
            self._connect_clipboard_signals()

    def _object_added_cb(self, object_id, name):
        """Emit an object-added GObject event when dbus event arrives"""
        self.emit('object-added', str(object_id), name)

    def _object_deleted_cb(self, object_id):
        """Emit an object-deleted GObject event when dbus event arrives"""
        self.emit('object-deleted', str(object_id))

    def _object_state_changed_cb(self, object_id, values):
        """Emit an object-state-changed GObject event when dbus event arrives
        
        GObject event has:
        
            object_id 
            name 
            percent 
            icon 
            preview
            activity 
        
        From the ClipboardObject instance which is being described.
        """
        self.emit('object-state-changed', str(object_id), values[NAME_KEY],
                  values[PERCENT_KEY], values[ICON_KEY], values[PREVIEW_KEY],
                  values[ACTIVITY_KEY])

    def add_object(self, name):
        """Add a new object to the path
        
        returns dbus path-name for the new object's cliboard service,
        this is used for all future references to the cliboard object.
        
        Note:
            That service is actually provided by the clipboard
            service object, not the ClipboardObject
        """
        return str(self._dbus_service.add_object(name))

    def add_object_format(self, object_id, formatType, data, on_disk):
        """Annotate given object on the clipboard with new information
        
        object_id -- dbus path as returned from add_object
        formatType -- XXX what should this be? mime type?
        data -- storage format for the clipped object?
        on_disk -- whether the data is on-disk (non-volatile) or in 
            memory (volatile)
        
        Last three arguments are just passed directly to the 
        clipboardobject.Format instance on the server side.
        
        returns None
        """
        self._dbus_service.add_object_format(dbus.ObjectPath(object_id),
                formatType,
                data,
                on_disk)
    
    def delete_object(self, object_id):
        """Remove the given object from the clipboard
        
        object_id -- dbus path as returned from add_object
        """
        self._dbus_service.delete_object(dbus.ObjectPath(object_id))
    
    def set_object_percent(self, object_id, percent):
        """Set the "percentage" for the given clipboard object 
        
        object_id -- dbus path as returned from add_object
        percentage -- numeric value from 0 to 100 inclusive
        
        Object percentages which are set to 100% trigger "file-completed"
        operations, see the backend ClipboardService's 
        _handle_file_completed method for details.
        
        returns None
        """
        self._dbus_service.set_object_percent(dbus.ObjectPath(object_id), percent)

    def get_object(self, object_id):
        """Retrieve the clipboard object structure for given object 
        
        object_id -- dbus path as returned from add_object
        
        Retrieves the metadata description of a given object, but 
        *not* the data for the object.  Use get_object_data passing 
        one of the values in the FORMATS_KEY value in order to 
        retrieve the data.
        
        returns dictionary with 
            NAME_KEY: str,
            PERCENT_KEY: number,
            ICON_KEY: str,
            PREVIEW_KEY: XXX what is it?,
            ACTIVITY_KEY: source activity id,
            FORMATS_KEY: list of XXX what is it?
        """
        return self._dbus_service.get_object(dbus.ObjectPath(object_id),)

    def get_object_data(self, object_id, formatType):    
        """Retrieve object's data in the given formatType
        
        object_id -- dbus path as returned from add_object
        formatType -- format specifier XXX of what description 
        
        returns data as a string
        """
        return self._dbus_service.get_object_data(dbus.ObjectPath(object_id),
                                                  formatType,
                                                  byte_arrays=True)
        
_clipboard_service = None
def get_instance():
    """Retrieve this process's interface to the clipboard service"""
    global _clipboard_service
    if not _clipboard_service:
        _clipboard_service = ClipboardService()
    return _clipboard_service
