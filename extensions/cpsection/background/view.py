# Copyright (C) 2012 Agustin Zubiaga <aguz@sugarlabs.org>
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
from sugar3.graphics.toolbutton import ToolButton
from jarabe.controlpanel.sectionview import SectionView
from jarabe.controlpanel.inlinealert import InlineAlert

from gettext import gettext as _


class Background(SectionView):

    def __init__(self, model, alerts):
        SectionView.__init__(self)

        self._model = model
        self._restart_alerts = alerts

        if 'background' in self._restart_alerts:
            self._restart_alert.props.msg = self.restart_msg
            self._restart_alert.show()

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

        sw = Gtk.ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC,
                      Gtk.PolicyType.AUTOMATIC)

        store = Gtk.ListStore(GdkPixbuf.Pixbuf, str)

        icon_view = Gtk.IconView.new_with_model(store)
        icon_view.set_selection_mode(Gtk.SelectionMode.SINGLE)
        icon_view.connect('selection-changed', self._background_selected,
                          store)
        icon_view.set_pixbuf_column(0)
        icon_view.grab_focus()

        pl = model.fill_background_list(store)
        self._select_background(icon_view, pl)
        sw.add(icon_view)

        self.pack_start(sw, True, True, 0)

        self._alert_box = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        self.pack_start(self._alert_box, False, False, 0)
        self._alert_box.show()

        self._restart_alert = InlineAlert()
        self._restart_alert.props.msg = self.restart_msg
        self._alert_box.pack_start(self._restart_alert, True, True, 0)

        self.setup()

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
        if image_path != self._model.BACKGROUND_CHOOSED:
            iter_ = store.get_iter(widget.get_selected_items()[0])
            image_path = store.get(iter_, 1)[0]
            self._model.set_background(image_path)
            self._restart_alerts.append('background')
            self.needs_restart = True
            self._alert_box.show()
            self._restart_alert.show()
        else:
            if 'background' in self.restart_alerts:
                self._restart_alerts.remove('background')
            self.needs_restart = False
            self._restart_alert.hide()

    def _select_background(self, icon_view, paths_list):
        background = self._model.get_background()
        if background in paths_list:
            _path = paths_list.index(background)
            path = Gtk.TreePath.new_from_string('%s' % _path)
            icon_view.select_path(path)
            self.needs_restart = False

    def _clear_clicked_cb(self, widget, event=None):
        self._model.set_background(None)
        self._restart_alerts.append('background')
        self.needs_restart = True
        self._alert_box.show()
        self._restart_alert.show()

    def setup(self):
        self.needs_restart = False
        self.show_all()
        self._restart_alert.hide()

    def undo(self):
        self._model.undo()
