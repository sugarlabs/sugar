# Copyright (C) 2006, Red Hat, Inc.
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
from gettext import gettext as _

from sugar.chat.sketchpad.SketchPad import SketchPad
import richtext

class ChatEditor(gtk.HBox):
    TEXT_MODE = 0
    SKETCH_MODE = 1

    def __init__(self, chat, mode):
        gtk.HBox.__init__(self, False, 6)

        self._chat = chat

        self._notebook = gtk.Notebook()
        self._notebook.set_show_tabs(False)
        self._notebook.set_show_border(False)
        self._notebook.set_size_request(-1, 70)
    
        chat_view_sw = gtk.ScrolledWindow()
        chat_view_sw.set_shadow_type(gtk.SHADOW_IN)
        chat_view_sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self._text_view = richtext.RichTextView()
        self._text_view.connect("key-press-event", self.__key_press_event_cb)
        chat_view_sw.add(self._text_view)
        self._text_view.show()
        
        self._notebook.append_page(chat_view_sw)
        chat_view_sw.show()
        
        self._sketchpad = SketchPad()
        self._notebook.append_page(self._sketchpad)
        self._sketchpad.show()
        
        self.pack_start(self._notebook)
        self._notebook.show()
        
        send_button = gtk.Button(_("Send"))
        send_button.set_size_request(60, -1)
        send_button.connect('clicked', self.__send_button_clicked_cb)
        self.pack_start(send_button, False, True)
        send_button.show()
        
        self.set_mode(mode)

    def set_color(self, color):
        self._sketchpad.set_color(color)
        
    def get_buffer(self):
        return self._text_view.get_buffer()

    def set_mode(self, mode):
        self._mode = mode
        if self._mode == ChatEditor.SKETCH_MODE:
            self._notebook.set_current_page(1)
        elif self._mode == ChatEditor.TEXT_MODE:
            self._notebook.set_current_page(0)

    def __send_button_clicked_cb(self, button):
        self._send()

    def _send(self):
        if self._mode == ChatEditor.SKETCH_MODE:
            self._send_sketch()
        elif self._mode == ChatEditor.TEXT_MODE:
            self._send_text()

    def _send_sketch(self):
        self._chat.send_sketch(self._sketchpad.to_svg())
        self._sketchpad.clear()

    def _send_text(self):
        buf = self._text_view.get_buffer()
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter())
        if len(text.strip()) > 0:
            serializer = richtext.RichTextSerializer()
            text = serializer.serialize(buf)
            self._chat.send_text_message(text)

        buf.set_text("")
        buf.place_cursor(buf.get_start_iter())
            
    def __key_press_event_cb(self, text_view, event):
        if event.keyval == gtk.keysyms.Return:
            self._send()
            return True
