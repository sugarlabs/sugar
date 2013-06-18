# Copyright (C) 2013 Ignacio Rodriguez <ignacio@sugarlabs.org>
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
from gi.repository import Gdk

from sugar3.graphics import style
from jarabe.controlpanel.sectionview import SectionView
from jarabe.controlpanel.inlinealert import InlineAlert

from gettext import gettext as _

import logging


class IconChange(SectionView):

    def __init__(self, model, alerts):
        SectionView.__init__(self)

        self._model = model
        self._restart_alerts = alerts

        if 'icon' in self._restart_alerts:
            self._restart_alert.props.msg = self.restart_msg
            self._restart_alert.show()

        self.set_border_width(style.DEFAULT_SPACING * 2)
        self.set_spacing(style.DEFAULT_SPACING)

        label_box = Gtk.HBox()
        label_bg = Gtk.Label(_('Select an icon:'))
        label_bg.modify_fg(Gtk.StateType.NORMAL,
                              style.COLOR_SELECTION_GREY.get_gdk_color())
        label_box.pack_start(label_bg, False, True, 0)
        self.pack_start(label_box, False, True, 1)

        sw = Gtk.ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC,
                      Gtk.PolicyType.AUTOMATIC)

        viewicons = self.__get_icon_box(model.get_icons())

        sw.add_with_viewport(viewicons)

        self.pack_start(sw, True, True, 0)

        self._alert_box = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        self.pack_start(self._alert_box, False, False, 0)
        self._alert_box.show()

        self._restart_alert = InlineAlert()
        self._restart_alert.props.msg = self.restart_msg
        self._alert_box.pack_start(self._restart_alert, True, True, 0)

        self.setup()

    def __get_icon_box(self, icons):
        box = Gtk.VBox()
        total = 0
        x = Gdk.Screen.width() / 10
        maxtotal = Gdk.Screen.width() / x
        maxtotal -= 2

        boxs = []
        last_box = Gtk.HBox()
        boxs.append(last_box)
        first = True

        for icon in icons:
            logging.debug('VIEW: %s' % (icon[1]))
            icon_box = Gtk.EventBox()
            icon_box.add(icon[0])
            icon[0].show()
            icon_box.show()        
            icon_box.connect('button-press-event', self.__icon_changed, icon[1])

            if first:
                self.first = icon_box
                self.last_icon = icon_box
                icon_box.set_sensitive(False)
                first = False

            last_box.pack_start(icon_box, False, False, 5)

            if total > 5:
                total = 0
                new_box = Gtk.HBox()
                last_box = new_box
                boxs.append(last_box)
            else:
                total += 1

        for box_icon in boxs:
            box.pack_start(box_icon, False, False, 5)

        box.show_all()
        return box

    def setup(self):

        self.needs_restart = False
        self.show_all()
        self._restart_alert.hide()

    def undo(self):
        self._model.undo()

    def __icon_changed(self, widget, event, icon):

        self.last_icon.set_sensitive(True)

        self.last_icon = widget

        widget.set_sensitive(False)

        self.icon_name = icon

        self._model.set_icon(icon)
        self._restart_alerts.append('icon')
        self.needs_restart = True
        self._alert_box.show()
        self._restart_alert.show()
