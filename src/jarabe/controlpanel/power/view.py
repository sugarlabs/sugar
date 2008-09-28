# Copyright (C) 2008, OLPC
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

import gtk
from gettext import gettext as _

from sugar.graphics import style

from jarabe.controlpanel.sectionview import SectionView
from jarabe.controlpanel.inlinealert import InlineAlert

class Power(SectionView):
    def __init__(self, model, alerts):
        SectionView.__init__(self)

        self._model = model
        self.restart_alerts = alerts
        self._automatic_pm_valid = True
        self._extreme_pm_valid = True
        self._extreme_pm_change_handler = None
        self._automatic_pm_change_handler = None

        self.set_border_width(style.DEFAULT_SPACING * 2)
        self.set_spacing(style.DEFAULT_SPACING)
        group = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)

        self._automatic_pm_alert_box = gtk.HBox(spacing=style.DEFAULT_SPACING)
        self._extreme_pm_alert_box = gtk.HBox(spacing=style.DEFAULT_SPACING)

        separator_pm = gtk.HSeparator()
        self.pack_start(separator_pm, expand=False)
        separator_pm.show()

        label_pm = gtk.Label(_('Power management'))
        label_pm.set_alignment(0, 0)
        self.pack_start(label_pm, expand=False)
        label_pm.show()
        box_pm = gtk.VBox()
        box_pm.set_border_width(style.DEFAULT_SPACING * 2)
        box_pm.set_spacing(style.DEFAULT_SPACING)

        box_automatic_pm = gtk.HBox(spacing=style.DEFAULT_SPACING)
        label_automatic_pm = gtk.Label(
            _('Automatic power management (increases battery life)'))
        label_automatic_pm.set_alignment(0, 0.5)
        self._automatic_button = gtk.CheckButton()
        self._automatic_button.set_alignment(0, 0)
        box_automatic_pm.pack_start(self._automatic_button, expand=False)
        box_automatic_pm.pack_start(label_automatic_pm, expand=False)
        self._automatic_button.show()
        label_automatic_pm.show()
        group.add_widget(label_automatic_pm)
        box_pm.pack_start(box_automatic_pm, expand=False)
        box_automatic_pm.show()

        self._automatic_pm_alert = InlineAlert()
        label_automatic_pm_error = gtk.Label()
        group.add_widget(label_automatic_pm_error)
        self._automatic_pm_alert_box.pack_start(label_automatic_pm_error,
                                                expand=False)
        label_automatic_pm_error.show()
        self._automatic_pm_alert_box.pack_start(self._automatic_pm_alert,
                                                expand=False)
        box_pm.pack_end(self._automatic_pm_alert_box, expand=False)
        self._automatic_pm_alert_box.show()
        if 'automatic_pm' in self.restart_alerts:
            self._automatic_pm_alert.props.msg = self.restart_msg
            self._automatic_pm_alert.show()

        box_extreme_pm = gtk.HBox(spacing=style.DEFAULT_SPACING)
        label_extreme_pm = gtk.Label(
                             _('Extreme power management (disables' \
                               'wireless radio, increases battery life)'))
        label_extreme_pm.set_alignment(0, 0.5)
        self._extreme_button = gtk.CheckButton()
        self._extreme_button.set_alignment(0, 0)
        box_extreme_pm.pack_start(self._extreme_button, expand=False)
        self._extreme_button.show()
        box_extreme_pm.pack_start(label_extreme_pm, expand=False)
        group.add_widget(label_extreme_pm)
        label_extreme_pm.show()
        box_pm.pack_start(box_extreme_pm, expand=False)
        box_extreme_pm.show()

        self._extreme_pm_alert = InlineAlert()
        label_extreme_pm_error = gtk.Label()
        group.add_widget(label_extreme_pm_error)
        self._extreme_pm_alert_box.pack_start(label_extreme_pm_error,
                                              expand=False)
        label_extreme_pm_error.show()
        self._extreme_pm_alert_box.pack_start(self._extreme_pm_alert,
                                              expand=False)
        box_pm.pack_end(self._extreme_pm_alert_box, expand=False)
        self._extreme_pm_alert_box.show()
        if 'extreme_pm' in self.restart_alerts:
            self._extreme_pm_alert.props.msg = self.restart_msg
            self._extreme_pm_alert.show()

        self.pack_start(box_pm, expand=False)
        box_pm.show()

        self.setup()

    def setup(self):
        try:
            automatic_state = self._model.get_automatic_pm()
            extreme_state = self._model.get_extreme_pm()

        except Exception, detail:
            self._automatic_pm_alert.props.msg = detail
            self._automatic_pm_alert.show()

            self._extreme_pm_alert.props.msg = detail
            self._extreme_pm_alert.show()
        else:
            self._automatic_button.set_active(automatic_state)
            self._extreme_button.set_active(extreme_state)

        self._extreme_pm_valid = True
        self._automatic_pm_valid = True
        self.needs_restart = False
        self._automatic_pm_change_handler = self._automatic_button.connect( \
                'toggled', self.__automatic_pm_toggled_cb)
        self._extreme_pm_change_handler = self._extreme_button.connect( \
                'toggled', self.__extreme_pm_toggled_cb)

    def undo(self):
        self._automatic_button.disconnect(self._automatic_pm_change_handler)
        self._extreme_button.disconnect(self._extreme_pm_change_handler)
        self._model.undo()
        self._extreme_pm_alert.hide()
        self._automatic_pm_alert.hide()

    def _validate(self):
        if self._extreme_pm_valid and self._automatic_pm_valid:
            self.props.is_valid = True
        else:
            self.props.is_valid = False

    def __automatic_pm_toggled_cb(self, widget, data=None):
        state = widget.get_active()
        try:
            self._model.set_automatic_pm(state)
        except Exception, detail:
            print detail
            self._automatic_pm_alert.props.msg = detail
        else:
            self._automatic_pm_valid = True

        self._validate()
        return False

    def __extreme_pm_toggled_cb(self, widget, data=None):
        state = widget.get_active()
        try:
            self._model.set_extreme_pm(state)
        except Exception, detail:
            print detail
            self._extreme_pm_alert.props.msg = detail
        else:
            self._extreme_pm_valid = True

        self._validate()
        return False
