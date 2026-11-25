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

from sugar3.graphics import style
from sugar3.graphics.radiotoolbutton import RadioToolButton
from jarabe.controlpanel.sectionview import SectionView

from gettext import gettext as _


class Background(SectionView):

    def __init__(self, model, alerts=None):
        SectionView.__init__(self)

        self._model = model
        self._images_loaded = False
        self._append_to_store_sid = None
        self._available_height = 0
        self._last_scrolled_height = None

        self.connect('realize', self.__realize_cb)
        self.connect('unrealize', self.__unrealize_cb)

        self.set_border_width(style.DEFAULT_SPACING * 2)
        self.set_spacing(style.DEFAULT_SPACING)

        label_box = Gtk.Box()
        label_bg = Gtk.Label(label=_('Select a background:'))
        label_bg.modify_fg(Gtk.StateType.NORMAL,
                           style.COLOR_SELECTION_GREY.get_gdk_color())
        label_bg.show()
        label_box.pack_start(label_bg, False, True, 0)
        label_box.show()
        self.pack_start(label_box, False, True, 1)

        clear_button = Gtk.Button()
        clear_button.set_label(_('Clear background'))
        clear_button.connect('clicked', self._clear_clicked_cb)
        clear_button.show()
        self.pack_end(clear_button, False, True, 0)

        self._grid_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._grid_box.connect('size-allocate',
                               self.__grid_box_size_allocate_cb)
        self.pack_start(self._grid_box, True, True, 0)
        self._grid_box.show()

        self._scrolled_window = Gtk.ScrolledWindow()
        self._scrolled_window.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        self._scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC,
                                         Gtk.PolicyType.AUTOMATIC)
        self._grid_box.pack_start(self._scrolled_window, False, False, 0)
        self._scrolled_window.show()

        self._store = Gtk.ListStore(GdkPixbuf.Pixbuf, str)

        self._icon_view = Gtk.IconView.new_with_model(self._store)
        self._icon_view.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._icon_view.connect('selection-changed', self._background_selected)
        self._icon_view.connect('size-allocate',
                                self.__icon_view_size_allocate_cb)
        self._icon_view.set_pixbuf_column(0)
        self._icon_view.grab_focus()
        self._scrolled_window.add(self._icon_view)
        self._icon_view.show()

        alpha = self._model.get_background_alpha_level()

        alpha_box = Gtk.HBox()
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
            button.show()
            alpha_box.pack_start(button, False, True, 0)
            alpha_buttons.append(button)

        for button in alpha_buttons:
            button.connect('toggled', self._set_alpha_cb)

        alpha_alignment = Gtk.Alignment()
        alpha_alignment.set(0.5, 0, 0, 0)
        alpha_alignment.add(alpha_box)
        alpha_box.show()
        self.pack_start(alpha_alignment, False, False, 0)
        alpha_alignment.show()

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
                self._store.append([pixbuf, file_path])
                self._paths_list.append(file_path)

            self._append_to_store_sid = GLib.idle_add(self._append_to_store,
                                                      file_paths)
        else:
            self._select_background()
            self._images_loaded = True
            window = self.get_window()
            if window is not None:
                window.set_cursor(None)
                Gdk.flush()
            self._append_to_store_sid = None

    def _cancel_append_to_store(self):
        if self._append_to_store_sid is not None:
            GLib.source_remove(self._append_to_store_sid)
            self._append_to_store_sid = None

    def __realize_cb(self, widget):
        if self._images_loaded:
            self.get_window().set_cursor(None)
        else:
            self.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))
        Gdk.flush()

    def __unrealize_cb(self, widget):
        self.get_window().set_cursor(None)
        Gdk.flush()

    def __grid_box_size_allocate_cb(self, widget, allocation):
        if (allocation.height > 1 and
                allocation.height != self._available_height):
            self._available_height = allocation.height
            self._update_scrolled_window_height()

    def __icon_view_size_allocate_cb(self, widget, allocation):
        if self._available_height > 1:
            self._update_scrolled_window_height()

    def _get_icon_view_row_metrics(self):
        item_padding = self._icon_view.get_item_padding()
        row_height = 0
        total_rows = 0

        for row in self._store:
            ok, rect = self._icon_view.get_cell_rect(row.path, None)
            if ok and rect.height > 0:
                row_height = max(row_height, rect.height + 2 * item_padding)
            item_row = self._icon_view.get_item_row(row.path)
            if item_row >= 0:
                total_rows = max(total_rows, item_row + 1)

        if row_height <= 0:
            row_height = style.XLARGE_ICON_SIZE + 2 * item_padding

        return row_height, total_rows

    def _update_scrolled_window_height(self):
        if self._available_height <= 1:
            return

        if len(self._store) == 0:
            target_height = self._available_height
        else:
            row_height, total_rows = self._get_icon_view_row_metrics()
            margin = self._icon_view.get_margin()
            row_spacing = self._icon_view.get_row_spacing()
            frame = style.LINE_WIDTH * 2

            content_avail = self._available_height - frame
            rows = (content_avail - 2 * margin + row_spacing) // (
                row_height + row_spacing)
            if total_rows > 0:
                rows = min(rows, total_rows)
            rows = max(1, rows)

            target_content_h = (2 * margin + rows * row_height +
                                (rows - 1) * row_spacing)
            target_height = min(self._available_height,
                                target_content_h + frame)

        if target_height != self._last_scrolled_height:
            self._last_scrolled_height = target_height
            self._scrolled_window.set_size_request(-1, target_height)

    def _set_alpha_cb(self, widget):
        if widget.get_active():
            self._model.set_background_alpha_level(widget.value)

    def _get_selected_path(self, widget):
        try:
            iter_ = self._store.get_iter(widget.get_selected_items()[0])
            image_path = self._store.get(iter_, 1)[0]

            return image_path, iter_
        except:
            return None

    def _background_selected(self, widget):
        selected = self._get_selected_path(widget)

        if selected is None:
            return

        image_path, _iter = selected
        iter_ = self._store.get_iter(widget.get_selected_items()[0])
        image_path = self._store.get(iter_, 1)[0]
        self._model.set_background_image_path(image_path)

    def _select_background(self):
        background = self._model.get_background_image_path()
        if background in self._paths_list:
            self._icon_view.select_path(
                Gtk.TreePath.new_from_string(
                    '%s' % self._paths_list.index(background)))

    def _clear_clicked_cb(self, widget, event=None):
        self._model.set_background_image_path(None)

    def setup(self):
        self.show_all()

    def apply(self):
        self._cancel_append_to_store()

    def undo(self):
        self._model.undo()
        self._cancel_append_to_store()
