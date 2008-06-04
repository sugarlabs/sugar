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

from sugar.graphics import style

from controlpanel.sectionview import SectionView
from controlpanel.inlinealert import InlineAlert

CLASS = 'Frame'
ICON = 'module-frame'
TITLE = _('Frame')

_never =  _('never')
_instantaneous = _('instantaneous')
_delay_label = _('Delay in milliseconds:')

class Frame(SectionView):
    def __init__(self, model, alerts):
        SectionView.__init__(self)

        self._model = model
        self._hot_delay_sid = 0
        self._hot_delay_is_valid = True
        self._hot_delay_change_handler = None
        self._warm_delay_sid = 0
        self._warm_delay_is_valid = True
        self._warm_delay_change_handler = None
        self.restart_alerts = alerts

        self.set_border_width(style.DEFAULT_SPACING * 2)
        self.set_spacing(style.DEFAULT_SPACING)
        self._group = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)        

        self._hot_delay_slider = None
        self._hot_delay_alert = None
        self._setup_hot_corners()

        self._warm_delay_slider = None
        self._warm_delay_alert = None
        self._setup_warm_edges()

        self.setup()

    def _setup_hot_corners(self):   
        separator_hot = gtk.HSeparator()
        self.pack_start(separator_hot, expand=False)
        separator_hot.show()

        label_hot_corners = gtk.Label(_('Hot Corners'))
        label_hot_corners.set_alignment(0, 0)
        self.pack_start(label_hot_corners, expand=False)
        label_hot_corners.show()

        box_hot_corners = gtk.VBox()
        box_hot_corners.set_border_width(style.DEFAULT_SPACING * 2)
        box_hot_corners.set_spacing(style.DEFAULT_SPACING)

        box_delay = gtk.HBox(spacing=style.DEFAULT_SPACING)
        label_delay = gtk.Label(_delay_label)
        label_delay.set_alignment(1, 0.75)
        label_delay.modify_fg(gtk.STATE_NORMAL, 
                              style.COLOR_SELECTION_GREY.get_gdk_color())
        box_delay.pack_start(label_delay, expand=False)
        self._group.add_widget(label_delay)
        label_delay.show()        
          
        adj = gtk.Adjustment(value=100, lower=0, upper=1000, step_incr=100, 
                             page_incr=100, page_size=0)
        self._hot_delay_slider = gtk.HScale(adj)
        self._hot_delay_slider.set_digits(0)
        self._hot_delay_slider.connect('format-value', 
                                       self.__hot_delay_format_cb)
        box_delay.pack_start(self._hot_delay_slider)
        self._hot_delay_slider.show()
        box_hot_corners.pack_start(box_delay, expand=False)
        box_delay.show()

        self._hot_delay_alert = InlineAlert()
        label_delay_error = gtk.Label()
        self._group.add_widget(label_delay_error)

        delay_alert_box = gtk.HBox(spacing=style.DEFAULT_SPACING)
        delay_alert_box.pack_start(label_delay_error, expand=False)
        label_delay_error.show()
        delay_alert_box.pack_start(self._hot_delay_alert, expand=False)
        box_hot_corners.pack_start(delay_alert_box, expand=False)
        delay_alert_box.show()
        if 'hot_delay' in self.restart_alerts:
            self._hot_delay_alert.props.msg = self.restart_msg
            self._hot_delay_alert.show()
        
        self.pack_start(box_hot_corners, expand=False)
        box_hot_corners.show()                

    def _setup_warm_edges(self):   
        separator_warm = gtk.HSeparator()
        self.pack_start(separator_warm, expand=False)
        separator_warm.show()

        label_warm_edges = gtk.Label(_('Warm Edges'))
        label_warm_edges.set_alignment(0, 0)
        self.pack_start(label_warm_edges, expand=False)
        label_warm_edges.show()

        box_warm_edges = gtk.VBox()
        box_warm_edges.set_border_width(style.DEFAULT_SPACING * 2)
        box_warm_edges.set_spacing(style.DEFAULT_SPACING)

        box_delay = gtk.HBox(spacing=style.DEFAULT_SPACING)
        label_delay = gtk.Label(_delay_label)
        label_delay.set_alignment(1, 0.75)
        label_delay.modify_fg(gtk.STATE_NORMAL, 
                              style.COLOR_SELECTION_GREY.get_gdk_color())
        box_delay.pack_start(label_delay, expand=False)
        self._group.add_widget(label_delay)
        label_delay.show()        
          
        adj = gtk.Adjustment(value=100, lower=0, upper=1000, step_incr=100, 
                             page_incr=100, page_size=0)
        self._warm_delay_slider = gtk.HScale(adj)
        self._warm_delay_slider.set_digits(0)
        self._warm_delay_slider.connect('format-value', 
                                       self.__warm_delay_format_cb)
        box_delay.pack_start(self._warm_delay_slider)
        self._warm_delay_slider.show()
        box_warm_edges.pack_start(box_delay, expand=False)
        box_delay.show()

        self._warm_delay_alert = InlineAlert()
        label_delay_error = gtk.Label()
        self._group.add_widget(label_delay_error)

        delay_alert_box = gtk.HBox(spacing=style.DEFAULT_SPACING)
        delay_alert_box.pack_start(label_delay_error, expand=False)
        label_delay_error.show()
        delay_alert_box.pack_start(self._warm_delay_alert, expand=False)
        box_warm_edges.pack_start(delay_alert_box, expand=False)
        delay_alert_box.show()
        if 'warm_delay' in self.restart_alerts:
            self._warm_delay_alert.props.msg = self.restart_msg
            self._warm_delay_alert.show()
        
        self.pack_start(box_warm_edges, expand=False)
        box_warm_edges.show()                
        
    def setup(self):
        self._hot_delay_slider.set_value(self._model.get_hot_corners_delay())
        self._warm_delay_slider.set_value(self._model.get_warm_edges_delay())
        self._hot_delay_is_valid = True
        self._warm_delay_is_valid = True
        self.needs_restart = False
        self._hot_delay_change_handler = self._hot_delay_slider.connect( \
                'value-changed', self.__hot_delay_changed_cb)
        self._warm_delay_change_handler = self._warm_delay_slider.connect( \
                'value-changed', self.__warm_delay_changed_cb)
            
    def undo(self):        
        self._hot_delay_slider.disconnect(self._hot_delay_change_handler)
        self._warm_delay_slider.disconnect(self._warm_delay_change_handler)
        self._model.undo()
        self._hot_delay_alert.hide()        
        self._warm_delay_alert.hide()        

    def __hot_delay_changed_cb(self, scale, data=None):        
        if self._hot_delay_sid:
            gobject.source_remove(self._hot_delay_sid)
        self._hot_delay_sid = gobject.timeout_add(self._APPLY_TIMEOUT, 
                                              self.__hot_delay_timeout_cb, 
                                              scale)
                
    def __hot_delay_timeout_cb(self, scale):        
        self._hot_delay_sid = 0
        if scale.get_value() == self._model.get_hot_corners_delay():       
            return
        try:
            self._model.set_hot_corners_delay(scale.get_value())
        except ValueError, detail:
            self._hot_delay_alert.props.msg = detail
            self._hot_delay_is_valid = False
            self.needs_restart = False
        else:
            self._hot_delay_alert.props.msg = self.restart_msg
            self._hot_delay_is_valid = True            
            self.needs_restart = True
            self.restart_alerts.append('hot_delay')
                        
        if self._hot_delay_is_valid:
            self.props.is_valid = True
        else:    
            self.props.is_valid = False

        self._hot_delay_alert.show()        
        return False

    def __hot_delay_format_cb(self, scale, value):
        if value == 1000.0:
            return _never
        elif value == 0.0:
            return _instantaneous
        else:
            return '%s ms' % value

    def __warm_delay_changed_cb(self, scale, data=None):        
        if self._warm_delay_sid:
            gobject.source_remove(self._warm_delay_sid)
        self._warm_delay_sid = gobject.timeout_add( \
                self._APPLY_TIMEOUT, self.__warm_delay_timeout_cb, scale)
                
    def __warm_delay_timeout_cb(self, scale):        
        self._warm_delay_sid = 0
        if scale.get_value() == self._model.get_warm_edges_delay():       
            return
        try:
            self._model.set_warm_edges_delay(scale.get_value())
        except ValueError, detail:
            self._warm_delay_alert.props.msg = detail
            self._warm_delay_is_valid = False
            self.needs_restart = False
        else:
            self._warm_delay_alert.props.msg = self.restart_msg
            self._warm_delay_is_valid = True            
            self.needs_restart = True
            self.restart_alerts.append('warm_delay')
                        
        if self._warm_delay_is_valid:
            self.props.is_valid = True
        else:    
            self.props.is_valid = False

        self._warm_delay_alert.show()        
        return False

    def __warm_delay_format_cb(self, scale, value):
        if value == 1000.0:
            return _never
        elif value == 0.0:
            return _instantaneous
        else:
            return '%s ms' % value
