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

import gtk

from sugar import _sugarext

from sugar.graphics.icon import _SVGLoader
import sugar.profile

ICON_ENTRY_PRIMARY = _sugarext.ICON_ENTRY_PRIMARY
ICON_ENTRY_SECONDARY = _sugarext.ICON_ENTRY_SECONDARY

class IconEntry(_sugarext.IconEntry):

    def __init__(self):
        _sugarext.IconEntry.__init__(self)

        self._clear_icon = None
        self._clear_shown = False

        self.connect('key_press_event', self._keypress_event_cb)

    def set_icon_from_name(self, position, name):
        icon_theme = gtk.icon_theme_get_default()
        icon_info = icon_theme.lookup_icon(name,
                                           gtk.ICON_SIZE_SMALL_TOOLBAR,
                                           0)

        if icon_info.get_filename().endswith('.svg'):
            loader = _SVGLoader()
            color = sugar.profile.get_color()
            entities = {'fill_color': color.get_fill_color(),
                        'stroke_color': color.get_stroke_color()}
            handle = loader.load(icon_info.get_filename(), entities, None)
            pixbuf = handle.get_pixbuf()
        else:
            pixbuf = gtk.gdk.pixbuf_new_from_file(icon_info.get_filename())
        del icon_info

        image = gtk.Image()
        image.set_from_pixbuf(pixbuf)
        image.show()

        self.set_icon(position, image)

    def set_icon(self, position, image):
        if image.get_storage_type() not in [gtk.IMAGE_PIXBUF, gtk.IMAGE_STOCK]:
            raise ValueError('Image must have a storage type of pixbuf or ' +
                             'stock, not %r.' % image.get_storage_type())
        _sugarext.IconEntry.set_icon(self, position, image)

    def remove_icon(self, position):
        _sugarext.IconEntry.set_icon(self, position, None)

    def add_clear_button(self):
        if self.props.text != "":
            self.show_clear_button()
        else:
            self.hide_clear_button()

        self.connect('icon-pressed', self._icon_pressed_cb)
        self.connect('changed', self._changed_cb)

    def show_clear_button(self):
        if not self._clear_shown:
            self.set_icon_from_name(ICON_ENTRY_SECONDARY,
                'dialog-cancel')
            self._clear_shown = True

    def hide_clear_button(self):
        if self._clear_shown:
            self.remove_icon(ICON_ENTRY_SECONDARY)
            self._clear_shown = False

    def _keypress_event_cb(self, widget, event):
        keyval = gtk.gdk.keyval_name(event.keyval)
        if keyval == 'Escape':
            self.props.text = ''
            return True
        return False

    def _icon_pressed_cb(self, entru, icon_pos, button):
        if icon_pos == ICON_ENTRY_SECONDARY:
            self.set_text('')
            self.hide_clear_button()

    def _changed_cb(self, icon_entry):
        if not self.props.text:
            self.hide_clear_button()
        else:
            self.show_clear_button()

