# Copyright (C) 2007, One Laptop Per Child
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import gettext

import gtk
import gobject
import hippo
import math
        
from sugar.graphics import style
from sugar.graphics.icon import Icon

_ = lambda msg: gettext.dgettext('sugar', msg)

class Alert(gtk.EventBox, gobject.GObject):
    """UI interface for Alerts

    Alerts are used inside the activity window instead of being a
    separate popup window. They do not hide canvas content. You can
    use add_alert(widget) and remove_alert(widget) inside your activity
    to add and remove the alert. The position of the alert is below the
    toolbox or top in fullscreen mode.

    Properties:
        'title': the title of the alert,
        'message': the message of the alert,
        'icon': the icon that appears at the far left
    See __gproperties__
    """

    __gtype_name__ = 'SugarAlert'

    __gsignals__ = {
        'response': (gobject.SIGNAL_RUN_FIRST,
                        gobject.TYPE_NONE, ([object]))
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
        self._hbox.set_border_width(style.DEFAULT_SPACING)
        self._hbox.set_spacing(style.DEFAULT_SPACING)
        self.add(self._hbox)

        self._title = None
        self._msg = None
        self._icon = None
        self._buttons = {}
        
        self._msg_box = gtk.VBox()
        self._title_label = gtk.Label()
        self._title_label.set_alignment(0, 0.5)
        self._msg_box.pack_start(self._title_label, False)
        self._title_label.show()

        self._msg_label = gtk.Label()
        self._msg_label.set_alignment(0, 0.5)
        self._msg_box.pack_start(self._msg_label, False)
        self._hbox.pack_start(self._msg_box, False)
        self._msg_label.show()
        
        self._buttons_box = gtk.HButtonBox()
        self._buttons_box.set_layout(gtk.BUTTONBOX_END)
        self._buttons_box.set_spacing(style.DEFAULT_SPACING)
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
                self._hbox.pack_start(self._icon, False)
                self._hbox.reorder_child(self._icon, 0)

    def do_get_property(self, pspec):
        if pspec.name == 'title':
            return self._title
        elif pspec.name == 'msg':
            return self._msg

    def add_button(self, response_id, label, icon=None, position=-1):
        """Add a button to the alert

        response_id: will be emitted with the response signal
                     a response ID should one of the pre-defined
                     GTK Response Type Constants or a positive number
        label: that will occure right to the buttom
        icon: this can be a SugarIcon or a gtk.Image
        position: the position of the button in the box (optional)
        """
        button = gtk.Button()
        self._buttons[response_id] = button
        if icon is not None:
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
        cancel_button = self.add_button(gtk.RESPONSE_CANCEL, _('Cancel'), icon)
        icon.show()

        icon = Icon(icon_name='dialog-ok')
        ok_button = self.add_button(gtk.RESPONSE_OK, _('Ok'), icon)
        icon.show()


class _TimeoutIcon(hippo.CanvasText, hippo.CanvasItem):
    __gtype_name__ = 'AlertTimeoutIcon'

    def __init__(self, **kwargs):
        hippo.CanvasText.__init__(self, **kwargs)
        
        self.props.orientation = hippo.ORIENTATION_HORIZONTAL
        self.props.border_left = style.DEFAULT_SPACING
        self.props.border_right = style.DEFAULT_SPACING
            
    def do_paint_background(self, cr, damaged_box):
        [width, height] = self.get_allocation()
        
        x = width * 0.5
        y = height * 0.5
        radius = min(width * 0.5, height * 0.5)         
        
        hippo.cairo_set_source_rgba32(cr, self.props.background_color)
        cr.arc(x, y, radius, 0, 2*math.pi)        
        cr.fill_preserve()    


class TimeoutAlert(Alert):
    """This is a ready-made two button (Cancel,Continue) alert

    It times out with a positive reponse after the given amount of seconds.
    """

    def __init__(self, timeout=5, **kwargs):
        Alert.__init__(self, **kwargs)

        self._timeout = timeout
        
        icon = Icon(icon_name='dialog-cancel')
        cancel_button = self.add_button(gtk.RESPONSE_CANCEL, _('Cancel'), icon)
        icon.show()
        
        self._timeout_text = _TimeoutIcon(
            text=self._timeout,
            color=style.COLOR_BUTTON_GREY.get_int(),
            background_color=style.COLOR_WHITE.get_int())    
        canvas = hippo.Canvas()
        canvas.set_root(self._timeout_text)
        canvas.show()                       
        self.add_button(gtk.RESPONSE_OK, _('Continue'), canvas)

        gobject.timeout_add(1000, self.__timeout)
        
    def __timeout(self):
        self._timeout -= 1
        self._timeout_text.props.text = self._timeout
        if self._timeout == 0:
            self._response(gtk.RESPONSE_OK)
            return False
        return True


class NotifyAlert(Alert):
    """Timeout alert with only an "OK" button - just for notifications"""

    def __init__(self, timeout=5, **kwargs):
        Alert.__init__(self, **kwargs)

        self._timeout = timeout

        self._timeout_text = _TimeoutIcon(
            text=self._timeout,
            color=style.COLOR_BUTTON_GREY.get_int(),
            background_color=style.COLOR_WHITE.get_int())
        canvas = hippo.Canvas()
        canvas.set_root(self._timeout_text)
        canvas.show()
        self.add_button(gtk.RESPONSE_OK, _('OK'), canvas)

        gobject.timeout_add(1000, self.__timeout)

    def __timeout(self):
        self._timeout -= 1
        self._timeout_text.props.text = self._timeout
        if self._timeout == 0:
            self._response(gtk.RESPONSE_OK)
            return False
        return True
