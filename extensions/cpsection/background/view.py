# Copyright (C) 2012 Agustin Zubiaga <aguz@sugarlabs.org>
# Copyright (C) 2013 Sugar Labs
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

from gi.repository import Gtk
from gi.repository import GdkPixbuf

from sugar3.graphics import style
from sugar3.graphics.radiotoolbutton import RadioToolButton
from jarabe.controlpanel.sectionview import SectionView

from gettext import gettext as _


class Background(SectionView):

    def __init__(self, model, alerts=None):
        SectionView.__init__(self)

        self._model = model

        self.set_border_width(style.DEFAULT_SPACING * 2)
        self.set_spacing(style.DEFAULT_SPACING)

        label_box = Gtk.Box()
        label_bg = Gtk.Label(label=_('Select a background:'))
        label_bg.modify_fg(Gtk.StateType.NORMAL,
                           style.COLOR_SELECTION_GREY.get_gdk_color())
        label_box.pack_start(label_bg, False, True, 0)
        self.pack_start(label_box, False, True, 1)

        clear_button = Gtk.Button()
        clear_button.set_label(_('Clear background'))
        clear_button.connect('clicked', self._clear_clicked_cb)
        clear_button.show()
        self.pack_end(clear_button, False, True, 0)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC,
                                   Gtk.PolicyType.AUTOMATIC)
        self.pack_start(scrolled_window, True, True, 0)
        scrolled_window.show()

        store = Gtk.ListStore(GdkPixbuf.Pixbuf, str)

        icon_view = Gtk.IconView.new_with_model(store)
        icon_view.set_selection_mode(Gtk.SelectionMode.SINGLE)
        icon_view.connect('selection-changed', self._background_selected,
                          store)
        icon_view.set_pixbuf_column(0)
        icon_view.grab_focus()
        scrolled_window.add(icon_view)
        icon_view.show()

        alpha = self._model.get_background_alpha_level()

        alpha_box = Gtk.HBox()
        alpha_buttons = []
        for i in ['000', '020', '040', '060', '080']:
            if len(alpha_buttons) > 0:
                alpha_buttons.append(RadioToolButton(group=alpha_buttons[0]))
            else:
                alpha_buttons.append(RadioToolButton(group=None))
            alpha_buttons[-1].set_icon_name('network-wireless-' + i)
            button_alpha_level = 1.0 - float(i) / 100.
            alpha_buttons[-1].connect('clicked', self._set_alpha_cb,
                                      button_alpha_level)
            alpha_box.pack_start(alpha_buttons[-1], False, True, 0)
            alpha_buttons[-1].show()
            if alpha < button_alpha_level + 0.1:
                alpha_buttons[-1].set_active(True)

        alpha_alignment = Gtk.Alignment()
        alpha_alignment.set(0.5, 0, 0, 0)
        alpha_alignment.add(alpha_box)
        alpha_box.show()
        self.pack_start(alpha_alignment, False, False, 0)
        alpha_alignment.show()

        paths_list = self._model.fill_background_list(store)
        self._select_background(icon_view, paths_list)

        self.setup()

    def _set_alpha_cb(self, widget, value):
        self._model.set_background_alpha_level(value)

    def _get_selected_path(self, widget, store):
        try:
            iter_ = store.get_iter(widget.get_selected_items()[0])
            image_path = store.get(iter_, 1)[0]

            return image_path, iter_
        except:
            return None

    def _background_selected(self, widget, store):
        selected = self._get_selected_path(widget, store)

        if selected is None:
            return

        image_path, _iter = selected
        iter_ = store.get_iter(widget.get_selected_items()[0])
        image_path = store.get(iter_, 1)[0]
        self._model.set_background_image_path(image_path)

    def _select_background(self, icon_view, paths_list):
        background = self._model.get_background_image_path()
        if background in paths_list:
            _path = paths_list.index(background)
            path = Gtk.TreePath.new_from_string('%s' % _path)
            icon_view.select_path(path)

    def _clear_clicked_cb(self, widget, event=None):
        self._model.set_background_image_path(None)

    def setup(self):
        self.show_all()

    def undo(self):
        self._model.undo()
