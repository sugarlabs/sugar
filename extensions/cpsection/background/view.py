# Copyright (C) 2012 Agustin Zubiaga <aguz@sugarlabs.org>
# Copyright (C) 2013 Sugar Labs
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GdkPixbuf

from sugar4.graphics import style
from sugar4.graphics.radiotoolbutton import RadioToolButton
from jarabe.controlpanel.sectionview import SectionView

from gettext import gettext as _


class Background(SectionView):

    def __init__(self, model, alerts=None):
        SectionView.__init__(self)

        self._model = model
        self._images_loaded = False
        self._append_to_store_sid = None

        self.connect('realize', self.__realize_cb)
        self.connect('unrealize', self.__unrealize_cb)

        self.set_margin_top(style.DEFAULT_SPACING * 2)
        self.set_margin_bottom(style.DEFAULT_SPACING * 2)
        self.set_margin_start(style.DEFAULT_SPACING * 2)
        self.set_margin_end(style.DEFAULT_SPACING * 2)
        self.set_spacing(style.DEFAULT_SPACING)

        label_box = Gtk.Box()
        label_bg = Gtk.Label(label=_('Select a background:'))
        style.apply_css_to_widget(label_bg, "* { color: %s; }" % style.COLOR_SELECTION_GREY.get_html())
        label_box.append(label_bg)
        self.append(label_box)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_has_frame(True)
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC,
                                   Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_vexpand(True)
        self.append(scrolled_window)

        alpha = self._model.get_background_alpha_level()

        alpha_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        alpha_buttons = []
        alpha_icons = [
            [1.0, 'network-wireless-000'],
            [0.8, 'network-wireless-020'],
            [0.6, 'network-wireless-040'],
            [0.4, 'network-wireless-060'],
            [0.2, 'network-wireless-080']]
        for value, icon_name in alpha_icons:
            if len(alpha_buttons) > 0:
                button = RadioToolButton(group=alpha_buttons[0])
            else:
                button = RadioToolButton(group=None)
            button.set_icon_name(icon_name)
            button.value = value
            button.props.active = value == alpha
            alpha_box.append(button)
            alpha_buttons.append(button)

        for button in alpha_buttons:
            button.connect('toggled', self._set_alpha_cb)

        alpha_box.set_halign(Gtk.Align.CENTER)
        self.append(alpha_box)

        clear_button = Gtk.Button()
        clear_button.set_label(_('Clear background'))
        clear_button.connect('clicked', self._clear_clicked_cb)
        clear_button.set_valign(Gtk.Align.END)
        self.append(clear_button)

        self._flow_box = Gtk.FlowBox()
        self._flow_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._flow_box.set_valign(Gtk.Align.START)
        self._flow_box.set_max_children_per_line(6)
        self._flow_box.set_column_spacing(6)
        self._flow_box.set_row_spacing(6)
        self._flow_box.set_homogeneous(True)
        self._flow_box.connect('selected-children-changed', self._background_selected)
        self._flow_box.grab_focus()
        scrolled_window.set_child(self._flow_box)

        self._paths_list = []

        file_paths = []
        for directory in self._model.BACKGROUNDS_DIRS:
            if directory is not None and os.path.exists(directory):
                for root, dirs, files in os.walk(directory):
                    for file_ in files:
                        file_paths.append(os.path.join(root, file_))

        self._append_to_store(file_paths)
        self.setup()

    def _append_to_store(self, file_paths):
        if file_paths:
            file_path = file_paths.pop()
            pixbuf = None

            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
                    file_path, style.XLARGE_ICON_SIZE,
                    style.XLARGE_ICON_SIZE)
            except GLib.GError:
                pass
            else:
                texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                picture = Gtk.Picture.new_for_paintable(texture)
                picture.set_size_request(style.XLARGE_ICON_SIZE, style.XLARGE_ICON_SIZE)
                
                child = Gtk.FlowBoxChild()
                child.set_child(picture)
                child._image_path = file_path
                self._flow_box.append(child)
                self._paths_list.append(file_path)

            self._append_to_store_sid = GLib.idle_add(self._append_to_store,
                                                      file_paths)
        else:
            self._select_background()
            self._images_loaded = True
            self.set_cursor(None)
            self._append_to_store_sid = None

    def _cancel_append_to_store(self):
        if self._append_to_store_sid is not None:
            GLib.source_remove(self._append_to_store_sid)
            self._append_to_store_sid = None

    def __realize_cb(self, widget):
        if self._images_loaded:
            self.set_cursor(None)
        else:
            self.set_cursor(Gdk.Cursor.new_from_name('wait', None))

    def __unrealize_cb(self, widget):
        self.set_cursor(None)

    def _set_alpha_cb(self, widget):
        if widget.get_active():
            self._model.set_background_alpha_level(widget.value)

    def _background_selected(self, flow_box):
        selected = flow_box.get_selected_children()
        if not selected:
            return
            
        child = selected[0]
        image_path = child._image_path
        self._model.set_background_image_path(image_path)

    def _select_background(self):
        background = self._model.get_background_image_path()
        if background in self._paths_list:
            index = self._paths_list.index(background)
            child = self._flow_box.get_child_at_index(index)
            if child:
                self._flow_box.select_child(child)

    def _clear_clicked_cb(self, widget, event=None):
        self._model.set_background_image_path(None)

    def setup(self):
        pass

    def apply(self):
        self._cancel_append_to_store()

    def undo(self):
        self._model.undo()
        self._cancel_append_to_store()
