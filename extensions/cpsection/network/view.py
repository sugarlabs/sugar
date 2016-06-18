# Copyright (C) 2008, OLPC
# Copyright (C) 2014, Sugar Labs, Frederick Grose
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


from gi.repository import Gtk
from gi.repository import Gdk
from gettext import gettext as _
from gi.repository import Gio
from gi.repository import Pango
from gi.repository import GLib

from sugar3.graphics.icon import Icon
from sugar3.graphics import style
from sugar3.graphics.alert import Alert

from jarabe.controlpanel.sectionview import SectionView
from jarabe.controlpanel.inlinealert import InlineAlert

import os

CLASS = 'Network'
ICON = 'module-network'
TITLE = _('Network')

_APPLY_TIMEOUT = 3000


def __setitem__(self, key, value):
    # set_value() aborts the program on an unknown key
    if key not in self:
        raise KeyError('unknown key: %r' % (key,))

    # determine type string of this key
    range = self.get_range(key)
    type_ = range.get_child_value(0).get_string()
    v = range.get_child_value(1)
    if type_ == 'type':
        # v is boxed empty array,
        # type of its elements is the allowed value type
        assert v.get_child_value(0).get_type_string().startswith('a')
        type_str = v.get_child_value(0).get_type_string()[1:]
    elif type_ == 'enum':
        # v is an array with the allowed values
        assert v.get_child_value(0).get_type_string().startswith('a')
        type_str = v.get_child_value(0).get_child_value(0).get_type_string()
    elif type_ == 'flags':
        # v is an array with the allowed values
        assert v.get_child_value(0).get_type_string().startswith('a')
        type_str = v.get_child_value(0).get_type_string()
    elif type_ == 'range':
        # type_str is a tuple giving the range
        assert v.get_child_value(0).get_type_string().startswith('(')
        type_str = v.get_child_value(0).get_type_string()[1]

    if not self.set_value(key, GLib.Variant(type_str, value)):
        raise ValueError("value '%s' for key '%s' is outside of"
                         " valid range" % (value, key))


def bind_with_convert(self, key, widget, prop, flags,
                      key_to_prop, prop_to_key):
    self._ignore_key_changed = False

    def key_changed(settings, key):
        if self._ignore_key_changed:
            return
        self._ignore_prop_changed = True
        widget.set_property(prop, key_to_prop(self[key]))
        self._ignore_prop_changed = False

    def prop_changed(widget, param):
        if self._ignore_prop_changed:
            return
        self._ignore_key_changed = True
        self[key] = prop_to_key(widget.get_property(prop))
        self._ignore_key_changed = False

    if not (flags & (Gio.SettingsBindFlags.SET | Gio.SettingsBindFlags.GET)):
        # ie Gio.SettingsBindFlags.DEFAULT
        flags |= Gio.SettingsBindFlags.SET | Gio.SettingsBindFlags.GET
    if flags & Gio.SettingsBindFlags.GET:
        key_changed(self, key)
        if not (flags & Gio.SettingsBindFlags.GET_NO_CHANGES):
            self.connect('changed::' + key, key_changed)
    if flags & Gio.SettingsBindFlags.SET:
        widget.connect('notify::' + prop, prop_changed)
    if not (flags & Gio.SettingsBindFlags.NO_SENSITIVITY):
        self.bind_writable(key, widget, "sensitive", False)

Gio.Settings.bind_with_convert = bind_with_convert
Gio.Settings.__setitem__ = __setitem__


def type_as_to_string(value):
    return ",".join(value)


def string_to_type_as(value):
    return value.split(',')


class NumberEntry(Gtk.Entry):
    def __init__(self):
        Gtk.Entry.__init__(self)
        self.connect('changed', self.on_changed)

    def on_changed(self, *args):
        text = self.get_text().strip()
        self.set_text(''.join([i for i in text if i in '0123456789']))


class SettingBox(Gtk.HBox):
    """
    Base class for "lines" on the screen representing configuration
    settings.
    """
    def __init__(self, name, size_group=None):
        Gtk.HBox.__init__(self, spacing=style.DEFAULT_SPACING)
        label = Gtk.Label(name)
        label.modify_fg(Gtk.StateType.NORMAL,
                        style.COLOR_SELECTION_GREY.get_gdk_color())
        label.set_alignment(1, 0.5)
        if size_group is not None:
            size_group.add_widget(label)
        self.pack_start(label, False, False, 0)
        label.show()


class ComboSettingBox(Gtk.VBox):
    """
    Container for sets of different settings selected by a top-level
    setting.

    Renders the top level setting as a ComboBox.  Only the currently
    active set is shown on screen.
    """
    def __init__(self, name, setting, setting_key,
                 option_sets, size_group=None):
        Gtk.VBox.__init__(self, spacing=style.DEFAULT_SPACING)

        setting_box = SettingBox(name, size_group)
        self.pack_start(setting_box, False, False, 0)
        setting_box.show()

        model = Gtk.ListStore(str, str, object)
        combo_box = Gtk.ComboBox(model=model)
        combo_box.connect('changed', self.__combo_changed_cb)
        setting_box.pack_start(combo_box, True, True, 0)
        combo_box.show()

        cell_renderer = Gtk.CellRendererText()
        cell_renderer.props.ellipsize = Pango.EllipsizeMode.MIDDLE
        cell_renderer.props.ellipsize_set = True
        combo_box.pack_start(cell_renderer, True)
        combo_box.add_attribute(cell_renderer, 'text', 0)
        combo_box.props.id_column = 1

        self._settings_box = Gtk.VBox()
        self._settings_box.show()
        self.pack_start(self._settings_box, False, False, 0)

        for optset in option_sets:
            model.append(optset)

        setting.bind(setting_key, combo_box, 'active-id',
                     Gio.SettingsBindFlags.DEFAULT)

    def __combo_changed_cb(self, combobox):
        giter = combobox.get_active_iter()
        new_box = combobox.get_model().get(giter, 2)[0]
        current_box = self._settings_box.get_children()
        if current_box:
            self._settings_box.remove(current_box[0])

        self._settings_box.add(new_box)
        new_box.show()


class OptionalSettingsBox(Gtk.VBox):
    """
    Container for settings (de)activated by a top-level setting.

    Renders the top level setting as a CheckButton. The settings are only
    shown on screen if the top-level setting is enabled.
    """
    def __init__(self, name, setting, setting_key, contents_box):
        Gtk.VBox.__init__(self, spacing=style.DEFAULT_SPACING)

        check_button = Gtk.CheckButton()
        check_button.props.label = name
        check_button.connect('toggled', self.__button_toggled_cb, contents_box)
        check_button.show()
        self.pack_start(check_button, True, True, 0)
        self.pack_start(contents_box, False, False, 0)

        setting.bind(setting_key, check_button, 'active',
                     Gio.SettingsBindFlags.DEFAULT)

    def __button_toggled_cb(self, check_button, contents_box):
        contents_box.set_visible(check_button.get_active())


class HostPortSettingBox(SettingBox):
    """
    A configuration line for a combined host name and port setting.
    """
    def __init__(self, name, alert, setting, size_group=None):
        SettingBox.__init__(self, name, size_group)
        self.pack_start(alert, False, True, 0)
        alert.hide()

        host_entry = Gtk.Entry()
        self.pack_start(host_entry, True, True, 0)
        host_entry.show()

        setting.bind('host', host_entry, 'text', Gio.SettingsBindFlags.DEFAULT)

        # port number 0 means n/a
        port_entry = NumberEntry()
        self.pack_start(port_entry, False, False, 0)
        port_entry.show()
        setting.bind_with_convert('port',
                                  port_entry,
                                  "text",
                                  Gio.SettingsBindFlags.GET |
                                  Gio.SettingsBindFlags.SET |
                                  Gio.SettingsBindFlags.NO_SENSITIVITY,
                                  lambda x: str(x),
                                  lambda x: int(x))


class StringSettingBox(SettingBox):
    """
    A configuration line for a string setting.
    """
    def __init__(self, name, setting, setting_key, size_group=None,
                 password_field=False):
        SettingBox.__init__(self, name, size_group)

        entry = Gtk.Entry()
        self.pack_start(entry, True, True, 0)
        entry.show()
        if password_field:
            entry.set_visibility(False)

        setting.bind(setting_key, entry, 'text', Gio.SettingsBindFlags.DEFAULT)


class StringSettingBox_with_convert(SettingBox):
    """
    A configuration line for a string setting.
    """
    def __init__(self, name, setting, setting_key,
                 get_method, set_method, size_group=None,
                 password_field=False):
        SettingBox.__init__(self, name, size_group)

        entry = Gtk.Entry()
        self.pack_start(entry, True, True, 0)
        entry.show()
        if password_field:
            entry.set_visibility(False)

        setting.bind_with_convert(setting_key,
                                  entry,
                                  "text",
                                  Gio.SettingsBindFlags.GET |
                                  Gio.SettingsBindFlags.SET |
                                  Gio.SettingsBindFlags.NO_SENSITIVITY,
                                  get_method,
                                  set_method)


class Network(SectionView):
    def __init__(self, model, alerts):
        SectionView.__init__(self)

        self._model = model
        self.restart_alerts = alerts
        self._jabber_sid = 0
        self._radio_valid = True
        self._jabber_change_handler = None
        self._radio_change_handler = None
        self._wireless_configuration_reset_handler = None
        self._start_jabber = self._model.get_jabber()
        self._proxy_settings = {}
        self._proxy_inline_alerts = {}

        self.set_border_width(style.DEFAULT_SPACING * 2)
        self.set_spacing(style.DEFAULT_SPACING)
        group = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)

        self._radio_alert_box = Gtk.HBox(spacing=style.DEFAULT_SPACING)

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

        separator_proxy = Gtk.HSeparator()
        workspace.pack_start(separator_proxy, False, False, 0)
        separator_proxy.show()

        self._add_proxy_section(workspace)

        self.setup()

    def _add_proxy_section(self, workspace):
        label_proxy = Gtk.Label(_('Proxy'))
        label_proxy.set_alignment(0, 0)
        workspace.pack_start(label_proxy, False, True, 0)
        label_proxy.show()

        box_proxy = Gtk.VBox()
        box_proxy.set_border_width(style.DEFAULT_SPACING * 2)
        box_proxy.set_spacing(style.DEFAULT_SPACING)
        workspace.pack_start(box_proxy, False, True, 0)
        box_proxy.show()

        self._proxy_alert = Alert()
        self._proxy_alert.props.title = _('Error')
        self._proxy_alert.props.msg = _('Proxy settings cannot be verified')
        box_proxy.pack_start(self._proxy_alert, False, False, 0)
        self._proxy_alert.connect('response', self._response_cb)
        self._proxy_alert.hide()

        # GSettings schemas for proxy:
        schemas = ['org.sugarlabs.system.proxy',
                   'org.sugarlabs.system.proxy.http',
                   'org.sugarlabs.system.proxy.https',
                   'org.sugarlabs.system.proxy.ftp',
                   'org.sugarlabs.system.proxy.socks']

        for schema in schemas:
            proxy_setting = Gio.Settings.new(schema)

            # We are not going to apply the settings immediatly.
            # We'll apply them if the user presses the "accept"
            # button, or we'll revert them if the user presses the
            # "cancel" button.
            proxy_setting.delay()
            alert = InlineAlert()

            self._proxy_settings[schema] = proxy_setting
            self._proxy_inline_alerts[schema] = alert

        size_group = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)

        automatic_proxy_box = Gtk.VBox(spacing=style.DEFAULT_SPACING)
        manual_proxy_box = Gtk.VBox(spacing=style.DEFAULT_SPACING)

        option_sets = [('None', 'none', Gtk.VBox()),
                       ('Use system proxy', 'system', Gtk.VBox()),
                       ('Manual', 'manual', manual_proxy_box),
                       ('Automatic', 'auto', automatic_proxy_box)]

        box_mode = ComboSettingBox(
            _('Method:'), self._proxy_settings['org.sugarlabs.system.proxy'],
            'mode', option_sets, size_group)

        box_proxy.pack_start(box_mode, False, False, 0)
        box_mode.show()

        url_box = StringSettingBox(
            _('Configuration URL:'),
            self._proxy_settings['org.sugarlabs.system.proxy'],
            'autoconfig-url',
            size_group)

        automatic_proxy_box.pack_start(url_box, True, True, 0)
        url_box.show()

        wpad_help_text = _('Web Proxy Autodiscovery is used when a'
                           ' Configuration URL is not provided. This is not'
                           ' recommended for untrusted public networks.')
        automatic_proxy_help = Gtk.Label(wpad_help_text)
        automatic_proxy_help.set_alignment(0, 0)
        automatic_proxy_help.set_line_wrap(True)
        automatic_proxy_help.show()
        automatic_proxy_box.pack_start(automatic_proxy_help, True, True, 0)

        # HTTP Section
        schema = 'org.sugarlabs.system.proxy.http'
        box_http = HostPortSettingBox(
            _('HTTP Proxy:'), self._proxy_inline_alerts[schema],
            self._proxy_settings[schema], size_group)
        manual_proxy_box.pack_start(box_http, False, False, 0)
        box_http.show()
        auth_contents_box = Gtk.VBox(spacing=style.DEFAULT_SPACING)
        auth_box = OptionalSettingsBox(
            _('Use authentication'),
            self._proxy_settings[schema],
            'use-authentication', auth_contents_box)
        manual_proxy_box.pack_start(auth_box, False, False, 0)
        auth_box.show()
        proxy_http_setting = Gio.Settings.new(schema)
        proxy_http_setting.delay()
        box_username = StringSettingBox(
            _('Username:'),
            self._proxy_settings[schema],
            'authentication-user', size_group)
        auth_contents_box.pack_start(box_username, False, False, 0)
        box_username.show()
        box_password = StringSettingBox(
            _('Password:'),
            self._proxy_settings[schema],
            'authentication-password', size_group, password_field=True)
        auth_contents_box.pack_start(box_password, False, False, 0)
        box_password.show()

        # HTTPS Section
        schema = 'org.sugarlabs.system.proxy.https'
        box_https = HostPortSettingBox(
            _('HTTPS Proxy:'), self._proxy_inline_alerts[schema],
            self._proxy_settings[schema],
            size_group)
        manual_proxy_box.pack_start(box_https, False, False, 0)
        box_https.show()

        # FTP Section
        schema = 'org.sugarlabs.system.proxy.ftp'
        box_ftp = HostPortSettingBox(
            _('FTP Proxy:'), self._proxy_inline_alerts[schema],
            self._proxy_settings[schema],
            size_group)
        manual_proxy_box.pack_start(box_ftp, False, False, 0)
        box_ftp.show()

        # SOCKS Section
        schema = 'org.sugarlabs.system.proxy.socks'
        box_socks = HostPortSettingBox(
            _('SOCKS Proxy:'), self._proxy_inline_alerts[schema],
            self._proxy_settings[schema],
            size_group)
        manual_proxy_box.pack_start(box_socks, False, False, 0)
        box_socks.show()

        box_ignore = StringSettingBox_with_convert(
            _('Ignore Hosts:'),
            self._proxy_settings['org.sugarlabs.system.proxy'], 'ignore-hosts',
            type_as_to_string, string_to_type_as, size_group)
        manual_proxy_box.pack_start(box_ignore, False, False, 0)
        box_ignore.show()

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

        self._radio_valid = True
        self.needs_restart = False
        self._radio_change_handler = self._button.connect(
            'toggled', self.__radio_toggled_cb)
        self._wireless_configuration_reset_handler =  \
            self._clear_wireless_button.connect(
                'clicked', self.__wireless_configuration_reset_cb)

    def _response_cb(self, alert, response_id):
        if response_id is Gtk.ResponseType.APPLY:
            self._proxy_alert.hide()
            self._apply_proxy_settings()
            self.show_restart_alert = True
            self.emit('add-alert')
        elif response_id is Gtk.ResponseType.CANCEL:
            self.undo()
            self._proxy_alert.remove_button(Gtk.ResponseType.APPLY)
            self._proxy_alert.remove_button(Gtk.ResponseType.CANCEL)
            self._proxy_alert.hide()
            self.emit('set-toolbar-sensitivity', True)

    def _ping_servers(self):
        response_to_return = True
        non_blank_host_name_counter = 0  # To check accidental blank hostnames
        for schema in list(self._proxy_settings.keys()):
                if (schema != 'org.sugarlabs.system.proxy'):
                    hostname = Gio.Settings.get_string(
                        self._proxy_settings[schema], 'host')
                    if hostname != '':
                        non_blank_host_name_counter += 1
                        response = os.system("ping -c 1 -W 1 " + hostname)
                        if (response):
                            self._proxy_inline_alerts[schema].show()
                            response_to_return = False
        if non_blank_host_name_counter == 0:
            response_to_return = False
        return response_to_return

    def _verify_settings(self):
        self._proxy_alert.props.title = _('Please Wait!')
        self._proxy_alert.props.msg = _('Proxy settings are being verified.')
        self._proxy_alert.show()
        flag_all_true = True
        g_proxy_schema = self._proxy_settings['org.sugarlabs.system.proxy']
        g_mode = Gio.Settings.get_string(g_proxy_schema, 'mode')
        self.show_restart_alert = False

        if g_mode == 'auto':
            flag_all_true = os.path.isfile(Gio.Settings.get_string(
                g_proxy_schema, 'autoconfig-url'))
        elif g_mode == 'manual':
            flag_all_true = self._ping_servers()
        if flag_all_true:
            self.show_restart_alert = True
            self._proxy_alert.hide()
            self._apply_proxy_settings()
        else:
            self._proxy_alert.props.title = _('Error!')
            self._proxy_alert.props.msg = _('The following setting(s) seems '
                                            'to be incorrect and may break '
                                            'your internet connection')

            icon = Icon(icon_name='dialog-cancel')
            self._proxy_alert.add_button(Gtk.ResponseType.APPLY,
                                         _('Break my internet'), icon)
            icon.show()
            icon = Icon(icon_name='dialog-ok')
            self._proxy_alert.add_button(Gtk.ResponseType.CANCEL,
                                         _('Reset'), icon)
            icon.show()

    def _apply_proxy_settings(self):
        for setting in self._proxy_settings.values():
            if (Gio.Settings.get_has_unapplied(setting)):
                setting.apply()

    def apply(self):
        self._apply_jabber(self._entry.get_text())
        self._model.set_social_help(self._social_help_entry.get_text())
        settings_changed = False
        for setting in self._proxy_settings.values():
            if (Gio.Settings.get_has_unapplied(setting)):
                settings_changed = True
        if settings_changed:
            self.needs_restart = True
            self._is_cancellable = False
            self.restart_msg = _('Proxy changes require restart')
            self._verify_settings()
        else:
            self.show_restart_alert = True

    def undo(self):
        self._button.disconnect(self._radio_change_handler)
        self._radio_alert.hide()
        for setting in self._proxy_settings.values():
            setting.revert()
        for alert in self._proxy_inline_alerts.values():
            alert.hide()

    def _validate(self):
        if self._radio_valid:
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

    def _apply_jabber(self, jabber):
        if jabber == self._model.get_jabber():
            return
        self._model.set_jabber(jabber)

    def __wireless_configuration_reset_cb(self, widget):
        # FIXME: takes effect immediately, not after CP is closed with
        # confirmation button
        self._model.clear_wireless_networks()
        self._clear_wireless_button.set_sensitive(False)
