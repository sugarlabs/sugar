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
import gettext
_ = lambda msg: gettext.dgettext('sugar', msg)

from sugar.graphics import style
from sugar.graphics.icon import Icon

from controlpanel.sectionview import SectionView
from controlpanel.inlinealert import InlineAlert

ICON = 'module-frame'
TITLE = _('Frame')

class Frame(SectionView):
    def __init__(self, model, alerts):
        SectionView.__init__(self)

        self._delay_sid = 0
        self._delay_valid = True
        self._top_valid = True
        self.restart_alerts = alerts

        self._model = model
        self._delay = self._model.get_delay()
        self._top_active = self._model.get_top_active()

        self.set_border_width(style.DEFAULT_SPACING * 2)
        self.set_spacing(style.DEFAULT_SPACING)
        group = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)

        self._delay_alert_box = gtk.HBox(spacing=style.DEFAULT_SPACING)
        self._top_alert_box = gtk.HBox(spacing=style.DEFAULT_SPACING)

        separator_delay = gtk.HSeparator()
        self.pack_start(separator_delay, expand=False)
        separator_delay.show()

        label_activation = gtk.Label(_('Activation'))
        label_activation.set_alignment(0, 0)
        self.pack_start(label_activation, expand=False)
        label_activation.show()
        box_activation = gtk.VBox()
        box_activation.set_border_width(style.DEFAULT_SPACING * 2)
        box_activation.set_spacing(style.DEFAULT_SPACING)
        box_delay = gtk.HBox(spacing=style.DEFAULT_SPACING)
        label_delay = gtk.Label(_('Delay:'))
        label_delay.set_alignment(1, 0.75)
        label_delay.modify_fg(gtk.STATE_NORMAL, 
                              style.COLOR_SELECTION_GREY.get_gdk_color())
        box_delay.pack_start(label_delay, expand=False)
        group.add_widget(label_delay)
        label_delay.show()        
          
        # (value, lower, upper, step_increment, page_increment, page_size)
        adj = gtk.Adjustment(100, 0, 1000, 100, 100, 0)
        self._scale = gtk.HScale(adj)
        self._scale.set_digits(0)
        self._scale.set_value(self._delay)
        box_delay.pack_start(self._scale)
        self._scale.show()
        self._scale.connect('value-changed', self.__delay_changed_cb)
        box_activation.pack_start(box_delay, expand=False)
        box_delay.show()

        icon_delay = Icon(icon_name='emblem-warning',
                          fill_color=style.COLOR_SELECTION_GREY.get_svg(),
                          stroke_color=style.COLOR_WHITE.get_svg())
        self._delay_alert = InlineAlert(icon=icon_delay)
        icon_delay.show()
        label_delay_error = gtk.Label()
        group.add_widget(label_delay_error)
        self._delay_alert_box.pack_start(label_delay_error, expand=False)
        label_delay_error.show()
        self._delay_alert_box.pack_start(self._delay_alert, expand=False)
        box_activation.pack_start(self._delay_alert_box, expand=False)
        self._delay_alert_box.show()
        try:                        
            self._delay_state = self._model.get_delay()        
        except Exception, detail:
            self._delay_alert.props.msg = detail                    
            self._delay_alert.show()
        if 'delay' in self.restart_alerts:
            self._delay_alert.props.msg = self._restart_msg
            self._delay_alert.show()

        box_top = gtk.HBox(spacing=style.DEFAULT_SPACING)
        label_top = gtk.Label(_('Top:'))
        label_top.set_alignment(1, 0.75)
        label_top.modify_fg(gtk.STATE_NORMAL, 
                              style.COLOR_SELECTION_GREY.get_gdk_color())
        box_top.pack_start(label_top, expand=False)
        group.add_widget(label_top)
        label_top.show()        
                
        self._button = gtk.CheckButton()
        self._button.set_alignment(0, 0)
        self._button.set_active(self._top_active)
        self._button.connect('toggled', self.__top_active_toggled_cb)
        box_top.pack_start(self._button, expand=False)
        self._button.show()
        box_activation.pack_start(box_top, expand=False)
        box_top.show()
  
        icon_top = Icon(icon_name='emblem-warning',
                        fill_color=style.COLOR_SELECTION_GREY.get_svg(),
                        stroke_color=style.COLOR_WHITE.get_svg())
        self._top_alert = InlineAlert(icon=icon_top)
        icon_top.show()
        label_top_error = gtk.Label()
        group.add_widget(label_top_error)
        self._top_alert_box.pack_start(label_top_error, expand=False)
        label_top_error.show()
        self._top_alert_box.pack_start(self._top_alert, expand=False)
        box_activation.pack_start(self._top_alert_box, expand=False)
        self._top_alert_box.show()
        try:                        
            self._top_state = self._model.get_top_active()        
        except Exception, detail:
            self._top_alert.props.msg = detail                    
            self._top_alert.show()
        if 'top_active' in self.restart_alerts:
            self._top_alert.props.msg = self._restart_msg
            self._top_alert.show()                
        
        self.pack_start(box_activation, expand=False)
        box_activation.show()                
        
    def undo(self):        
        self._model.set_delay(self._delay)
        self._model.set_top_active(self._top_active)
        self._scale.set_value(self._delay)
        self._button.set_active(self._top_active)
        if self._top_alert.props.visible:
            self._top_alert.hide()

        self._delay_valid = True
        self._top_valid = True
        self.restart = False
        self.restart_alerts = []

    def __top_active_toggled_cb(self, widget, data=None): 
        state = ('off', 'on')[widget.get_active()]
        try:
            self._model.set_top_active(state)
        except Exception, detail:
            self._top_alert.props.msg = detail
            self._top_valid = False
        else:
            self._top_alert.props.msg = self._restart_msg
            self._top_valid = True            
            if state != self._top_active:                
                self.restart = True
                self.restart_alerts.append('top_active')                
            else:
                self.restart = False

        if self._top_valid and self._delay_valid:
            self.props.valid_section = True
        else:    
            self.props.valid_section = False

        if not self._top_alert.props.visible or \
                state != self._top_active:                
            self._top_alert.show()
        else:    
            self._top_alert.hide()

        return False

    def __delay_changed_cb(self, widget, data=None):        
        if self._delay_sid:
            gobject.source_remove(self._delay_sid)
        self._delay_sid = gobject.timeout_add(1000, 
                                              self.__delay_timeout_cb, widget)
                
    def __delay_timeout_cb(self, widget):        
        self._delay_sid = 0
        try:
            self._model.set_delay(widget.get_value())
        except ValueError, detail:
            self._delay_alert.props.msg = detail
            self._delay_valid = False
        else:
            self._delay_alert.props.msg = self._restart_msg
            self._delay_valid = True            
            if widget.get_value() != self._delay:                
                self.restart = True
                self.restart_alerts.append('delay')
            else:
                self.restart = False

        if self._delay_valid:
            self.props.valid_section = True
        else:    
            self.props.valid_section = False

        if not self._delay_alert.props.visible or \
                widget.get_value() != self._delay:                
            self._delay_alert.show()
        else:    
            self._delay_alert.hide()

        return False
