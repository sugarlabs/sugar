import gtk
import gobject
import pango

from sugar.graphics import style

class InlineAlert(gtk.EventBox):
    """UI interface for Inline alerts

    Alerts are used inside the activity window instead of being a
    separate popup window. They do not hide canvas content. You can
    use add_alert(widget) and remove_alert(widget) inside your activity
    to add and remove the alert. The position of the alert is below the
    toolbox or top in fullscreen mode.

    Properties:
        'message': the message of the alert,
        'icon': the icon that appears at the far left
    See __gproperties__
    """

    __gtype_name__ = 'SugarInlineAlert'

    __gproperties__ = {
        'msg'    : (str, None, None, None,
                    gobject.PARAM_READWRITE),
        'msg'    : (str, None, None, None,
                    gobject.PARAM_READWRITE),
        'icon'   : (object, None, None,
                    gobject.PARAM_WRITABLE)
        }

    def __init__(self, **kwargs):

        self._msg = None
        self._msg_color = None
        self._icon = None

        self._hbox = gtk.HBox()
        self._hbox.set_spacing(style.DEFAULT_SPACING)

        self._msg_label = gtk.Label()
        self._msg_label.set_max_width_chars(50)
        self._msg_label.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
        self._msg_label.set_alignment(0, 0.5)
        self._msg_label.modify_fg(gtk.STATE_NORMAL, 
                                  style.COLOR_SELECTION_GREY.get_gdk_color())
        self._hbox.pack_start(self._msg_label, False)
        
        gobject.GObject.__init__(self, **kwargs)

        self.set_visible_window(True)        
        self.modify_bg(gtk.STATE_NORMAL, 
                       style.COLOR_WHITE.get_gdk_color())
        self.add(self._hbox)        
        self._msg_label.show()
        self._hbox.show()
        
    def do_set_property(self, pspec, value):        
        if pspec.name == 'msg':
            if self._msg != value:
                self._msg = value
                self._msg_label.set_markup(self._msg)
        elif pspec.name == 'icon':
            if self._icon != value:
                self._icon = value
                self._hbox.pack_start(self._icon, False)
                self._hbox.reorder_child(self._icon, 0)

    def do_get_property(self, pspec):
        if pspec.name == 'msg':
            return self._msg
