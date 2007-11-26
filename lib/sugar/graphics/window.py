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

import gobject
import gtk
import logging

from sugar.graphics.icon import Icon

class UnfullscreenButton(gtk.Window):

    def __init__(self):
        gtk.Window.__init__(self)

        self.set_decorated(False)
        self.set_resizable(False)
        self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)

        self.set_border_width(0)

        self.props.accept_focus = False

        #Setup estimate of width, height
        w, h = gtk.icon_size_lookup(gtk.ICON_SIZE_LARGE_TOOLBAR)
        self._width = w
        self._height = h

        self.connect('size-request', self._size_request_cb)

        screen = self.get_screen()
        screen.connect('size-changed', self._screen_size_changed_cb)

        self._button = gtk.Button()
        self._button.set_relief(gtk.RELIEF_NONE)

        self._icon = Icon(icon_name='view-return',
                            icon_size=gtk.ICON_SIZE_LARGE_TOOLBAR)
        self._icon.show()
        self._button.add(self._icon)

        self._button.show()
        self.add(self._button)

    def connect_button_press(self, cb):
        self._button.connect('button-press-event', cb)

    def _reposition(self):
        x = gtk.gdk.screen_width() - self._width
        self.move(x, 0)

    def _size_request_cb(self, widget, req):
        self._width = req.width
        self._height = req.height
        self._reposition()

    def _screen_size_changed_cb(self, screen):
        self._reposition()

class Window(gtk.Window):

    __gproperties__ = {
        'enable-fullscreen-mode': (bool, None, None, True,
                                    gobject.PARAM_READWRITE),
    }

    def __init__(self, **args):
        self._enable_fullscreen_mode = True

        gtk.Window.__init__(self, **args)

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

        self._event_box = gtk.EventBox()
        self._hbox.pack_start(self._event_box)
        self._event_box.show()
        
        self.add(self._vbox)
        self._vbox.show()

        self._is_fullscreen = False
        self._unfullscreen_button = UnfullscreenButton()
        self._unfullscreen_button.set_transient_for(self)
        self._unfullscreen_button.connect_button_press(
            self.__unfullscreen_button_pressed)

    def do_get_property(self, prop):
        if prop.name == 'enable-fullscreen-mode':
            return self._enable_fullscreen_mode
        else:
            return gtk.Window.do_get_property(self, prop)

    def do_set_property(self, prop, val):
        if prop.name == 'enable-fullscreen-mode':
            self._enable_fullscreen_mode = val
        else:
            gtk.Window.do_set_property(self, prop, val)

    def set_canvas(self, canvas):
        if self.canvas:
            self._event_box.remove(self.canvas)

        if canvas:
            self._event_box.add(canvas)
        
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
        if not (event.changed_mask & gtk.gdk.WINDOW_STATE_FULLSCREEN):
            return False

        if event.new_window_state & gtk.gdk.WINDOW_STATE_FULLSCREEN:
            if self.toolbox is not None:
                self.toolbox.hide()
            if self.tray is not None:
                self.tray.hide()

            self._is_fullscreen = True
            if self.props.enable_fullscreen_mode:
                self._unfullscreen_button.show()

        else:
            if self.toolbox is not None:
                self.toolbox.show()
            if self.tray is not None:
                self.tray.show()

            self._is_fullscreen = False
            if self.props.enable_fullscreen_mode:
                self._unfullscreen_button.hide()

    def __key_press_cb(self, widget, event):
        key = gtk.gdk.keyval_name(event.keyval)
        if event.state & gtk.gdk.MOD1_MASK:
            if key == 'space':
                self.tray.props.visible = not self.tray.props.visible
                return True
        elif key == 'Escape' and self._is_fullscreen and \
            self.props.enable_fullscreen_mode:
            self.unfullscreen()
            return True
        return False

    def __unfullscreen_button_pressed(self, widget, event):
        self.unfullscreen()
