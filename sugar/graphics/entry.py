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
import math
import logging

import gobject
import gtk
import hippo

from sugar.graphics import units
from sugar.graphics import color
from sugar.graphics import font
from sugar.graphics.iconbutton import IconButton
from sugar.graphics.roundbox import RoundBox

class Entry(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'SugarEntry'

    __gproperties__ = {
        'text'    : (str, None, None, None,
                      gobject.PARAM_READWRITE)
    }

    __gsignals__ = {
        'button-activated': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([int]))
    }
    
    def __init__(self, text=''):
        hippo.CanvasBox.__init__(self, orientation=hippo.ORIENTATION_HORIZONTAL)
        self.props.yalign = hippo.ALIGNMENT_CENTER

        self._buttons = {}

        self._round_box = RoundBox()
        self._round_box.props.border_color = color.FRAME_BORDER.get_int()
        self.append(self._round_box, hippo.PACK_EXPAND)

        self._entry = self.create_entry()
        self._entry.props.has_frame = False
        self._entry.props.text = text
        self._update_colors(focused=False)
        self._entry.modify_text(gtk.STATE_SELECTED,
                                color.BLACK.get_gdk_color())
        self._entry.connect('focus-in-event', self._entry_focus_in_event_cb)
        self._entry.connect('focus-out-event', self._entry_focus_out_event_cb)
        self._entry.connect('activate', self._entry_activate_cb)
        self._entry.modify_font(font.DEFAULT.get_pango_desc())
                
        self._canvas_widget = hippo.CanvasWidget()
        self._canvas_widget.props.widget = self._entry
        self._round_box.append(self._canvas_widget, hippo.PACK_EXPAND)

    def create_entry(self):
        """
        Subclasses can override this method in order to provide a different
        entry widget.
        """
        return gtk.Entry()

    def add_button(self, icon_name, action_id):
        button = IconButton(icon_name=icon_name)

        button.props.scale = units.SMALL_ICON_SCALE
        
        button.props.yalign = hippo.ALIGNMENT_CENTER
        button.props.xalign = hippo.ALIGNMENT_START
        
        button.connect('activated', self._button_activated_cb)
        self._round_box.append(button)
        self._buttons[button] = action_id

    def do_set_property(self, pspec, value):
        self._entry.set_property(pspec.name, value)

    def do_get_property(self, pspec):
        return self._entry.get_property(pspec.name)

    def _entry_focus_in_event_cb(self, widget, event):
        self._update_colors(focused=True)
        self.emit_paint_needed(0, 0, -1, -1)

    def _entry_focus_out_event_cb(self, widget, event):
        self._update_colors(focused=False)
        self.emit_paint_needed(0, 0, -1, -1)

    def _entry_activate_cb(self, entry):
        self.emit_activated()

    def _button_activated_cb(self, button):
        self.emit('button-activated', self._buttons[button])

    def _update_colors(self, focused):
        if focused:
            self._round_box.props.background_color = \
                    color.ENTRY_BACKGROUND_FOCUSED.get_int()

            self._entry.modify_base(gtk.STATE_NORMAL,
                                    color.ENTRY_BACKGROUND_FOCUSED.get_gdk_color())
            self._entry.modify_base(gtk.STATE_SELECTED,
                                    color.ENTRY_SELECTION_FOCUSED.get_gdk_color())
            self._entry.modify_text(gtk.STATE_NORMAL,
                                    color.ENTRY_TEXT_FOCUSED.get_gdk_color())
        else:
            self._round_box.props.background_color = \
                    color.ENTRY_BACKGROUND_UNFOCUSED.get_int()
        
            self._entry.modify_base(gtk.STATE_NORMAL,
                                    color.ENTRY_BACKGROUND_UNFOCUSED.get_gdk_color())
            self._entry.modify_base(gtk.STATE_SELECTED,
                                    color.ENTRY_SELECTION_UNFOCUSED.get_gdk_color())
            self._entry.modify_text(gtk.STATE_NORMAL,
                                    color.ENTRY_TEXT_UNFOCUSED.get_gdk_color())
