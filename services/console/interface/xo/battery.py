#!/usr/bin/env python

# Copyright (C) 2007, Eduardo Silva (edsiper@gmail.com).
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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import gtk
import gobject

from label import Label

class XO_Battery(gtk.Fixed):

    def __init__(self):
        gtk.Fixed.__init__(self)

        self.frame = gtk.Frame('Battery Status')
        self.set_border_width(10)
                
        self._battery_charge = self._get_battery_status()

        self._battery_drw = gtk.DrawingArea()
        self._battery_drw.set_size_request(70, 150)
        self._battery_drw.connect("expose-event", self.do_expose)

        fixed = gtk.Fixed();
        fixed.set_border_width(10)
        fixed.add(self._battery_drw)

        hbox = gtk.HBox(False, 0)
        hbox.pack_start(fixed, False, False, 4)
        
        # Battery info
        table = gtk.Table(2, 2)
        table.set_border_width(5)
        table.set_col_spacings(7)
        table.set_row_spacings(7)
        
        label_charge = Label('Charge: ' , Label.DESCRIPTION)
        self.label_charge_value = Label(str(self._battery_charge) + '%', Label.DESCRIPTION)
        
        table.attach(label_charge, 0, 1, 0, 1)
        table.attach(self.label_charge_value, 1,2, 0,1)

        # Charging
        """
        hbox_charging = gtk.HBox(False, 2)
        l_charging = gtk.Label('Charging: ')
        l_charging.set_justify(gtk.JUSTIFY_LEFT)
        hbox_charging.pack_start(l_charging, False, False, 0)
        
        self._label_charging = gtk.Label('No')
        self._label_charging.set_justify(gtk.JUSTIFY_LEFT)
        
        hbox_charging.pack_start(self._label_charging, False, False, 0)
        """
        
        alignment = gtk.Alignment(0,0,0,0)
        alignment.add(table)

        hbox.pack_start(alignment, False, False, 0)
        self.frame.add(hbox)
        self.add(self.frame)
        self.show_all()

        # Update every 2 seconds
        gobject.timeout_add(2000, self._update_battery_status)
        
    def _update_battery_status(self):
        
        self._battery_charge = self._get_battery_status()
        self.label_charge_value.set_text(str(self._battery_charge) + '%')
        self._battery_drw.queue_draw()
        return True

    def do_expose(self, widget, event):
        context = widget.window.cairo_create()
        
        [width, height] = widget.size_request()
        context.rectangle(0, 0, width, height)

        context.set_source_rgb (0,0,0)
        context.fill_preserve()
        context.stroke()
        
        self._draw_battery_usage(context, width, height)

    def _get_battery_status(self):
        battery_class_path = '/sys/class/battery/psu_0/'
        capacity_path = battery_class_path + 'capacity_percentage'
        try:
            f = open(capacity_path, 'r')
            val = f.read().split('\n')
            capacity = int(val[0])
            f.close()
        except:
            capacity = 0

        return capacity
        
    def _draw_battery_usage(self, context, width, height):
        
        usage_height = (self._battery_charge*height)/100

        context.rectangle(0, height - usage_height, width, height)
        
        if self._battery_charge > 50:
            context.set_source_rgb (0,1,0)
        
        if self._battery_charge > 10 and self._battery_charge <= 50:
            context.set_source_rgb (1,1,0)
            
        if self._battery_charge <= 10:
            context.set_source_rgb (1,0,0)

        context.fill_preserve()
