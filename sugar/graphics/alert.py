from gettext import gettext as _

import gtk
import gobject

from sugar.graphics import style
from sugar.graphics.icon import Icon


class Alert(gtk.EventBox, gobject.GObject):
    """UI interface for Alerts

    Alerts are used inside the activity window instead of being a
    separate popup window. They do not hide canvas content. You can
    use add_alert(widget) and remove_alert(widget) inside your activity
    to add and remove the alert. You can set the position (bottom=-1,
    top=0,1) for alerts global for the window by changing alert_position,
    default is bottom. 

    Properties:
        'title': the title of the alert,
        'message': the message of the alert,
        'icon': the icon that appears at the far left
    See __gproperties__
    """

    __gtype_name__ = 'SugarAlert'

    __gsignals__ = {
        'response': (gobject.SIGNAL_RUN_FIRST,
                        gobject.TYPE_NONE, ([int]))
        }

    __gproperties__ = {
        'title'  : (str, None, None, None,
                    gobject.PARAM_READWRITE),
        'msg'    : (str, None, None, None,
                    gobject.PARAM_READWRITE),
        'icon'   : (object, None, None,
                    gobject.PARAM_WRITABLE)
        }

    def __init__(self, **kwargs):
        gobject.GObject.__init__(self)

        self.set_visible_window(True)
        self._hbox = gtk.HBox()
        self.add(self._hbox)

        self._title = None
        self._msg = None
        self._icon = None
        self._timeout = 0
        self._buttons = {}

        self._msg_box = gtk.VBox()
        self._title_label = gtk.Label()
        size = style.zoom(style.GRID_CELL_SIZE * 0.5)
        self._title_label.set_alignment(0, 0.5)
        self._title_label.set_padding(style.DEFAULT_SPACING, 0)
        self._msg_box.pack_start(self._title_label, False)
        self._title_label.show()

        self._msg_label = gtk.Label()
        self._msg_label.set_alignment(0, 0.5)
        self._msg_label.set_padding(style.DEFAULT_SPACING, 0)
        self._msg_box.pack_start(self._msg_label, False)
        self._msg_label.show()
        self._hbox.pack_start(self._msg_box)

        self._buttons_box = gtk.HButtonBox()
        self._buttons_box.set_layout(gtk.BUTTONBOX_SPREAD)
        self._hbox.pack_start(self._buttons_box)
        self._buttons_box.show()

        self._msg_box.show()

        self._hbox.show()
        self.show()

    def do_set_property(self, pspec, value):
        if pspec.name == 'title':
            if self._title != value:
                self._title = value
                self._title_label.set_markup("<b>" + self._title + "</b>")
        elif pspec.name == 'msg':
            if self._msg != value:
                self._msg = value
                self._msg_label.set_markup(self._msg)
        elif pspec.name == 'icon':
            if self._icon != value:
                self._icon = value
                self._hbox.pack_start(self._icon)
                self._hbox.reorder_child(self._icon, 0)

    def do_get_property(self, pspec):
        if pspec.name == 'title':
            return self._title
        elif pspec.name == 'msg':
            return self._msg

    def add_button(self, response_id, label, icon, position=-1):
        """Add a button to the alert

        response_id: will be emitted with the response signal
        label: that will occure right to the buttom
        icon: this can be a SugarIcon or a gtk.Image
        position: the position of the button in the box (optional)
        """
        button = gtk.Button()
        self._buttons[response_id] = button
        button.set_image(icon)
        button.set_label(label)
        self._buttons_box.pack_start(button)
        button.show()
        button.connect('clicked', self.__button_clicked_cb, response_id)
        if position != -1:
            self._buttons_box.reorder_child(button, position)
        return button

    def remove_button(self, response_id):
        """Remove a button from the alert by the given button id"""
        self._buttons_box.remove(self._buttons[id])

    def _response(self, id):
        """Emitting response when we have a result

        A result can be that a user has clicked a button or
        a timeout has occured, the id identifies the button
        that has been clicked and -1 for a timeout
        """
        self.emit('response', id)

    def __button_clicked_cb(self, button, response_id):
        self._response(response_id)


class ConfirmationAlert(Alert):
    """This is a ready-made two button (Cancel,Ok) alert"""

    def __init__(self, **kwargs):
        Alert.__init__(self, **kwargs)

        icon = Icon(icon_name='dialog-cancel')
        cancel_button = self.add_button(0, _('Cancel'), icon)
        icon.show()

        icon = Icon(icon_name='dialog-ok')
        ok_button = self.add_button(1, _('Ok'), icon)
        icon.show()


