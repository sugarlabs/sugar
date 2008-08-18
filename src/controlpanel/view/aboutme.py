# Copyright (C) 2008, OLPC
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

import gtk
import gobject
from gettext import gettext as _

from sugar.graphics.icon import Icon
from sugar.graphics import style
from sugar.graphics.xocolor import XoColor
from sugar import profile

from controlpanel.sectionview import SectionView
from controlpanel.inlinealert import InlineAlert

CLASS = 'AboutMe'
ICON = 'module-about_me'
COLOR = profile.get_color()
TITLE = _('About Me')

class EventIcon(gtk.EventBox):
    __gtype_name__ = "SugarEventIcon"    
    def __init__(self, **kwargs):         
        gtk.EventBox.__init__(self)

        self.icon = Icon(pixel_size = style.XLARGE_ICON_SIZE, **kwargs)
        
        self.set_visible_window(False)
        self.set_app_paintable(True)
        self.set_events(gtk.gdk.BUTTON_PRESS_MASK)

        self.add(self.icon)
        self.icon.show()

class ColorPicker(EventIcon):
    __gsignals__ = {
        'color-changed': (gobject.SIGNAL_RUN_FIRST,
                          gobject.TYPE_NONE,
                          ([object]))
    }
    def __init__(self, xocolor=None):
        EventIcon.__init__(self)
        self.icon.props.xo_color = xocolor
        self.icon.props.icon_name = 'computer-xo'
        self.icon.props.pixel_size = style.XLARGE_ICON_SIZE
        self.connect('button_press_event', self.__pressed_cb)

    def __pressed_cb(self, button, event):
        self._set_random_colors()

    def _set_random_colors(self):
        xocolor = XoColor()
        self.icon.props.xo_color = xocolor
        self.emit('color-changed', xocolor)

class AboutMe(SectionView):
    def __init__(self, model, alerts):
        SectionView.__init__(self)

        self._model = model
        self.restart_alerts = alerts
        self._nick_sid = 0
        self._color_valid = True
        self._nick_valid = True
        self._color_change_handler = None
        self._nick_change_handler = None

        self.set_border_width(style.DEFAULT_SPACING * 2)
        self.set_spacing(style.DEFAULT_SPACING)
        self._group = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)

        self._nick_box = gtk.HBox(spacing=style.DEFAULT_SPACING)
        self._nick_alert_box = gtk.HBox(spacing=style.DEFAULT_SPACING)
        self._nick_entry = None
        self._nick_alert = None
        self._setup_nick()

        self._color_box = gtk.HBox(spacing=style.DEFAULT_SPACING)
        self._color_alert_box = gtk.HBox(spacing=style.DEFAULT_SPACING)
        self._color_picker = None
        self._color_alert = None
        self._setup_color()        

        self.setup()

    def _setup_nick(self):
        label_entry = gtk.Label(_('Name:'))
        label_entry.modify_fg(gtk.STATE_NORMAL, 
                              style.COLOR_SELECTION_GREY.get_gdk_color())
        self._group.add_widget(label_entry)
        label_entry.set_alignment(1, 0.5)
        self._nick_box.pack_start(label_entry, expand=False)
        label_entry.show()

        self._nick_entry = gtk.Entry()                
        self._nick_entry.modify_bg(gtk.STATE_INSENSITIVE, 
                                   style.COLOR_WHITE.get_gdk_color())
        self._nick_entry.modify_base(gtk.STATE_INSENSITIVE, 
                                     style.COLOR_WHITE.get_gdk_color())
        self._nick_entry.set_width_chars(25)
        self._nick_box.pack_start(self._nick_entry, expand=False)
        self._nick_entry.show()        

        label_entry_error = gtk.Label()
        self._group.add_widget(label_entry_error)
        self._nick_alert_box.pack_start(label_entry_error, expand=False)
        label_entry_error.show()

        self._nick_alert = InlineAlert()
        self._nick_alert_box.pack_start(self._nick_alert)
        if 'nick' in self.restart_alerts:
            self._nick_alert.props.msg = self.restart_msg
            self._nick_alert.show()

        self.pack_start(self._nick_box, False)
        self.pack_start(self._nick_alert_box, False)
        self._nick_box.show()
        self._nick_alert_box.show()
    
    def _setup_color(self):                
        label_color = gtk.Label(_('Click to change your color:'))
        label_color.modify_fg(gtk.STATE_NORMAL, 
                              style.COLOR_SELECTION_GREY.get_gdk_color())
        self._group.add_widget(label_color)
        self._color_box.pack_start(label_color, expand=False)
        label_color.show()
        
        self._color_picker = ColorPicker()
        self._color_box.pack_start(self._color_picker, expand=False)
        self._color_picker.show()

        label_color_error = gtk.Label()
        self._group.add_widget(label_color_error)
        self._color_alert_box.pack_start(label_color_error, expand=False)
        label_color_error.show()

        self._color_alert = InlineAlert()
        self._color_alert_box.pack_start(self._color_alert)
        if 'color' in self.restart_alerts:
            self._color_alert.props.msg = self.restart_msg
            self._color_alert.show()

        self.pack_start(self._color_box, False)
        self.pack_start(self._color_alert_box, False)        
        self._color_box.show()
        self._color_alert_box.show()
    
    def setup(self):
        self._nick_entry.set_text(self._model.get_nick())
        self._color_picker.icon.props.xo_color = self._model.get_color_xo()

        self._color_valid = True
        self._nick_valid = True
        self.needs_restart = False
        self._nick_change_handler = self._nick_entry.connect( \
                'changed', self.__nick_changed_cb)
        self._color_change_handler = self._color_picker.connect( \
                'color-changed', self.__color_changed_cb)

    def undo(self):
        self._color_picker.disconnect(self._color_change_handler)
        self._nick_entry.disconnect(self._nick_change_handler)
        self._model.undo()
        self._nick_alert.hide()
        self._color_alert.hide()        

    def __nick_changed_cb(self, widget, data=None):        
        if self._nick_sid:
            gobject.source_remove(self._nick_sid)
        self._nick_sid = gobject.timeout_add(self._APPLY_TIMEOUT, 
                                             self.__nick_timeout_cb, widget)

    def __nick_timeout_cb(self, widget):        
        self._nick_sid = 0

        if widget.get_text() == self._model.get_nick():
            return False
        try:
            self._model.set_nick(widget.get_text())
        except ValueError, detail:
            self._nick_alert.props.msg = detail
            self._nick_valid = False
        else:
            self._nick_alert.props.msg = self.restart_msg
            self._nick_valid = True            
            self.needs_restart = True
            self.restart_alerts.append('nick')
                        
        if self._nick_valid and self._color_valid:
            self.props.is_valid = True
        else:    
            self.props.is_valid = False

        self._nick_alert.show()
        return False

    def __color_changed_cb(self, colorpicker, xocolor):        
        self._model.set_color_xo(xocolor)
        self.needs_restart = True
        self._color_alert.props.msg = self.restart_msg
        self._color_valid = True
        self.restart_alerts.append('color')

        if self._nick_valid and self._color_valid:
            self.props.is_valid = True            
        else:    
            self.props.is_valid = False
        
        self._color_alert.show()
            



        

