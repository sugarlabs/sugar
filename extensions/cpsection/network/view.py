# Copyright (C) 2008, OLPC
# Copyright (C) 2014, Sugar Labs, Frederick Grose
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
from gettext import gettext as _

from sugar3.graphics import style

from jarabe.controlpanel.sectionview import SectionView
from jarabe.controlpanel.inlinealert import InlineAlert


CLASS = 'Network'
ICON = 'module-network'
TITLE = _('Network')


class Network(SectionView):
    def __init__(self, model, alerts):
        SectionView.__init__(self)

        self._model = model
        self.restart_alerts = alerts
        self._jabber_sid = 0
        self._jabber_valid = True
        self._radio_valid = True
        self._jabber_change_handler = None
        self._radio_change_handler = None
        self._wireless_configuration_reset_handler = None
        self._start_jabber = self._model.get_jabber()

        self.set_border_width(style.DEFAULT_SPACING * 2)
        self.set_spacing(style.DEFAULT_SPACING)
        group = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)

        self._radio_alert_box = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        self._jabber_alert_box = Gtk.HBox(spacing=style.DEFAULT_SPACING)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.add(scrolled)
        scrolled.show()

        workspace = Gtk.VBox()
        scrolled.add_with_viewport(workspace)
        workspace.show()

        separator_wireless = Gtk.HSeparator()
        workspace.pack_start(separator_wireless, False, True, 0)
        separator_wireless.show()

        label_wireless = Gtk.Label(label=_('Wireless'))
        label_wireless.set_alignment(0, 0)
        workspace.pack_start(label_wireless, False, True, 0)
        label_wireless.show()
        box_wireless = Gtk.VBox()
        box_wireless.set_border_width(style.DEFAULT_SPACING * 2)
        box_wireless.set_spacing(style.DEFAULT_SPACING)

        radio_info = Gtk.Label(label=_('The wireless radio may be turned'
                                       ' off to save battery life.'))
        radio_info.set_alignment(0, 0)
        radio_info.set_line_wrap(True)
        radio_info.show()
        box_wireless.pack_start(radio_info, False, True, 0)

        box_radio = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        self._button = Gtk.CheckButton()
        self._button.set_alignment(0, 0)
        box_radio.pack_start(self._button, False, True, 0)
        self._button.show()

        label_radio = Gtk.Label(label=_('Radio'))
        label_radio.set_alignment(0, 0.5)
        box_radio.pack_start(label_radio, False, True, 0)
        label_radio.show()

        box_wireless.pack_start(box_radio, False, True, 0)
        box_radio.show()

        self._radio_alert = InlineAlert()
        self._radio_alert_box.pack_start(self._radio_alert, False, True, 0)
        box_radio.pack_end(self._radio_alert_box, False, True, 0)
        self._radio_alert_box.show()
        if 'radio' in self.restart_alerts:
            self._radio_alert.props.msg = self.restart_msg
            self._radio_alert.show()

        wireless_info = Gtk.Label(
            label=_('Discard wireless connections if'
                    ' you have trouble connecting to the network'))
        wireless_info.set_alignment(0, 0)
        wireless_info.set_line_wrap(True)
        wireless_info.show()
        box_wireless.pack_start(wireless_info, False, True, 0)

        box_clear_wireless = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        self._clear_wireless_button = Gtk.Button()
        self._clear_wireless_button.set_label(
            _('Discard wireless connections'))
        box_clear_wireless.pack_start(
            self._clear_wireless_button, False, True, 0)
        if not self._model.have_wireless_networks():
            self._clear_wireless_button.set_sensitive(False)
        self._clear_wireless_button.show()
        box_wireless.pack_start(box_clear_wireless, False, True, 0)
        box_clear_wireless.show()

        workspace.pack_start(box_wireless, False, True, 0)
        box_wireless.show()

        separator_mesh = Gtk.HSeparator()
        workspace.pack_start(separator_mesh, False, False, 0)
        separator_mesh.show()

        label_mesh = Gtk.Label(label=_('Collaboration'))
        label_mesh.set_alignment(0, 0)
        workspace.pack_start(label_mesh, False, True, 0)
        label_mesh.show()
        box_mesh = Gtk.VBox()
        box_mesh.set_border_width(style.DEFAULT_SPACING * 2)
        box_mesh.set_spacing(style.DEFAULT_SPACING)

        server_info = Gtk.Label(_("The server is the equivalent of what"
                                  " room you are in; people on the same server"
                                  " will be able to see each other, even when"
                                  " they aren't on the same network."))
        server_info.set_alignment(0, 0)
        server_info.set_line_wrap(True)
        box_mesh.pack_start(server_info, False, True, 0)
        server_info.show()

        box_server = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        label_server = Gtk.Label(label=_('Server:'))
        label_server.set_alignment(1, 0.5)
        label_server.modify_fg(Gtk.StateType.NORMAL,
                               style.COLOR_SELECTION_GREY.get_gdk_color())
        box_server.pack_start(label_server, False, True, 0)
        group.add_widget(label_server)
        label_server.show()
        self._entry = Gtk.Entry()
        self._entry.set_alignment(0)
        self._entry.set_size_request(int(Gdk.Screen.width() / 3), -1)
        box_server.pack_start(self._entry, False, True, 0)
        self._entry.show()
        box_mesh.pack_start(box_server, False, True, 0)
        box_server.show()

        self._jabber_alert = InlineAlert()
        label_jabber_error = Gtk.Label()
        group.add_widget(label_jabber_error)
        self._jabber_alert_box.pack_start(label_jabber_error, False, True, 0)
        label_jabber_error.show()
        self._jabber_alert_box.pack_start(self._jabber_alert, False, True, 0)
        box_mesh.pack_end(self._jabber_alert_box, False, True, 0)
        self._jabber_alert_box.show()
        if 'jabber' in self.restart_alerts:
            self._jabber_alert.props.msg = self.restart_msg
            self._jabber_alert.show()

        social_help_info = Gtk.Label(
            _('Social Help is a forum that lets you connect with developers'
              ' and discuss Sugar Activities.  Changing servers means'
              ' discussions will happen in a different place with'
              ' different people.'))
        social_help_info.set_alignment(0, 0)
        social_help_info.set_line_wrap(True)
        box_mesh.pack_start(social_help_info, False, True, 0)
        social_help_info.show()

        social_help_box = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        social_help_label = Gtk.Label(label=_('Social Help Server:'))
        social_help_label.set_alignment(1, 0.5)
        social_help_label.modify_fg(Gtk.StateType.NORMAL,
                                    style.COLOR_SELECTION_GREY.get_gdk_color())
        social_help_box.pack_start(social_help_label, False, True, 0)
        group.add_widget(social_help_label)
        social_help_label.show()

        self._social_help_entry = Gtk.Entry()
        self._social_help_entry.set_alignment(0)
        self._social_help_entry.set_size_request(
            int(Gdk.Screen.width() / 3), -1)
        social_help_box.pack_start(self._social_help_entry, False, True, 0)
        self._social_help_entry.show()
        box_mesh.pack_start(social_help_box, False, True, 0)
        social_help_box.show()

        workspace.pack_start(box_mesh, False, True, 0)
        box_mesh.show()

        self.setup()

    def setup(self):
        self._entry.set_text(self._start_jabber)
        self._social_help_entry.set_text(self._model.get_social_help())

        try:
            radio_state = self._model.get_radio()
        except self._model.ReadError, detail:
            self._radio_alert.props.msg = detail
            self._radio_alert.show()
        else:
            self._button.set_active(radio_state)

        self._jabber_valid = True
        self._radio_valid = True
        self.needs_restart = False
        self._radio_change_handler = self._button.connect(
            'toggled', self.__radio_toggled_cb)
        self._wireless_configuration_reset_handler =  \
            self._clear_wireless_button.connect(
                'clicked', self.__wireless_configuration_reset_cb)

    def apply(self):
        self.apply_jabber(self._entry.get_text())
        self._model.set_social_help(self._social_help_entry.get_text())

    def undo(self):
        self._button.disconnect(self._radio_change_handler)
        self._jabber_alert.hide()
        self._radio_alert.hide()

    def _validate(self):
        if self._jabber_valid and self._radio_valid:
            self.props.is_valid = True
        else:
            self.props.is_valid = False

    def __radio_toggled_cb(self, widget, data=None):
        radio_state = widget.get_active()
        try:
            self._model.set_radio(radio_state)
        except self._model.ReadError, detail:
            self._radio_alert.props.msg = detail
            self._radio_valid = False
        else:
            self._radio_valid = True
            if self._model.have_wireless_networks():
                self._clear_wireless_button.set_sensitive(True)

        self._validate()
        return False

    def apply_jabber(self, jabber):
        if jabber == self._model.get_jabber:
            return
        try:
            self._model.set_jabber(jabber)
        except self._model.ReadError, detail:
            self._jabber_alert.props.msg = detail
            self._jabber_valid = False
            self._jabber_alert.show()
            self.restart_alerts.append('jabber')
        else:
            self._jabber_valid = True
            self._jabber_alert.hide()

        self._validate()
        return False

    def __wireless_configuration_reset_cb(self, widget):
        # FIXME: takes effect immediately, not after CP is closed with
        # confirmation button
        self._model.clear_wireless_networks()
        self._clear_wireless_button.set_sensitive(False)
