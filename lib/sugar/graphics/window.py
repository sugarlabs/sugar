# Copyright (C) 2007, Red Hat, Inc.
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

import gtk

class Window(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self)

        self.connect('realize', self.__window_realize_cb)
        self.connect('window-state-event', self.__window_state_event_cb)
        self.connect('key-press-event', self.__key_press_cb)
        
        self.toolbox = None
        self._alerts = []
        self.canvas = None
        self.tray = None
        
        self._vbox = gtk.VBox()
        self._hbox = gtk.HBox()
        self._vbox.pack_start(self._hbox)
        self._hbox.show()
        
        self.add(self._vbox)
        self._vbox.show()

    def set_canvas(self, canvas):
        if self.canvas:
            self._hbox.remove(self.canvas)

        self._hbox.pack_start(canvas)       
        
        self.canvas = canvas

    def set_toolbox(self, toolbox):
        if self.toolbox:
            self._vbox.remove(self.toolbox)
            
        self._vbox.pack_start(toolbox, False)
        self._vbox.reorder_child(toolbox, 0)
        
        self.toolbox = toolbox

    def set_tray(self, tray, position):
        if self.tray:
            box = self.tray.get_parent() 
            box.remove(self.tray)
                
        if position == gtk.POS_LEFT:
            self._hbox.pack_start(tray, False)
        elif position == gtk.POS_RIGHT:
            self._hbox.pack_end(tray, False)
        elif position == gtk.POS_BOTTOM:
            self._vbox.pack_end(tray, False)
                    
        self.tray = tray

    def add_alert(self, alert):
        self._alerts.append(alert)
        if len(self._alerts) == 1:
            self._vbox.pack_start(alert, False)
            if self.toolbox is not None:
                self._vbox.reorder_child(alert, 1)
            else:   
                self._vbox.reorder_child(alert, 0)
                
    def remove_alert(self, alert):
        if alert in self._alerts:
            self._alerts.remove(alert)
            # if the alert is the visible one on top of the queue
            if alert.get_parent() is not None:                            
                self._vbox.remove(alert)
                if len(self._alerts) >= 1:
                    self._vbox.pack_start(self._alerts[0], False)
                    if self.toolbox is not None:
                        self._vbox.reorder_child(self._alerts[0], 1)
                    else:
                        self._vbox.reorder_child(self._alert[0], 0)
                    
    def __window_realize_cb(self, window):
        group = gtk.Window()
        group.realize()
        window.window.set_group(group.window)

    def __window_state_event_cb(self, window, event):
        if event.new_window_state & gtk.gdk.WINDOW_STATE_FULLSCREEN:
            if self.toolbox is not None:
                self.toolbox.hide()
            if self.tray is not None:
                self.tray.hide()
        elif event.new_window_state == 0:
            if self.toolbox is not None:
                self.toolbox.show()
            if self.tray is not None:
                self.tray.show()

    def __key_press_cb(self, widget, event):
        if event.state & gtk.gdk.MOD1_MASK:
            if gtk.gdk.keyval_name(event.keyval) == 'space':
                self.tray.props.visible = not self.tray.props.visible
                return True
        return False
    
    def get_canvas_screenshot(self):
        if not self.canvas:
            return None

        window = self.canvas.window
        width, height = window.get_size()

        screenshot = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, has_alpha=False,
                                    bits_per_sample=8, width=width, height=height)
        screenshot.get_from_drawable(window, window.get_colormap(), 0, 0, 0, 0,
                                     width, height)
        return screenshot
