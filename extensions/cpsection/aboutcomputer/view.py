# coding=utf-8
# Copyright (C) 2008, OLPC
# Copyright (C) 2009 Simon Schampijer
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


from gettext import gettext as _

from gi.repository import Gtk, Pango
from gi.repository import Gdk

from sugar3.graphics import style

from jarabe import config
from jarabe.controlpanel.sectionview import SectionView


class AboutComputer(SectionView):
    def __init__(self, model, alerts=None):
        SectionView.__init__(self)

        self._model = model

        self.set_border_width(style.DEFAULT_SPACING * 2)
        self.set_spacing(style.DEFAULT_SPACING)

        self._group = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)

        scrollwindow = Gtk.ScrolledWindow()
        scrollwindow.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.pack_start(scrollwindow, True, True, 0)
        scrollwindow.show()

        self._vbox = Gtk.VBox()
        scrollwindow.add_with_viewport(self._vbox)
        self._vbox.show()

        self._setup_identity()

        self._setup_software()
        self._setup_copyright()

    def create_information_box(self, label_text, value_text):
        box = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        label = Gtk.Label(label=label_text)
        label.set_alignment(1, 0)
        label.modify_fg(Gtk.StateType.NORMAL,
                        style.COLOR_SELECTION_GREY.get_gdk_color())
        box.pack_start(label, False, True, 0)
        self._group.add_widget(label)
        label.show()
        value = Gtk.Label(label=value_text)
        value.set_alignment(0, 0)
        box.pack_start(value, False, True, 0)
        value.show()
        box.show()
        return box

    def _setup_identity(self):
        separator_identity = Gtk.HSeparator()
        self._vbox.pack_start(separator_identity, False, True, 0)
        separator_identity.show()

        label_identity = Gtk.Label(label=_('Identity'))
        label_identity.set_alignment(0, 0)
        self._vbox.pack_start(label_identity, False, True, 0)
        label_identity.show()
        vbox_identity = Gtk.VBox()
        vbox_identity.set_border_width(style.DEFAULT_SPACING * 2)
        vbox_identity.set_spacing(style.DEFAULT_SPACING)

        hardware_model = self._model.get_hardware_model()
        if hardware_model:
            vbox_identity.pack_start(
                self.create_information_box(_('Model:'), hardware_model),
                False, True, 0)

        vbox_identity.pack_start(
            self.create_information_box(_('Serial Number:'),
                                        self._model.get_serial_number()),
            False, True, 0)

        self._vbox.pack_start(vbox_identity, False, True, 0)
        vbox_identity.show()

    def _setup_software(self):
        separator_software = Gtk.HSeparator()
        self._vbox.pack_start(separator_software, False, True, 0)
        separator_software.show()

        label_software = Gtk.Label(label=_('Software'))
        label_software.set_alignment(0, 0)
        self._vbox.pack_start(label_software, False, True, 0)
        label_software.show()
        box_software = Gtk.VBox()
        box_software.set_border_width(style.DEFAULT_SPACING * 2)
        box_software.set_spacing(style.DEFAULT_SPACING)

        box_software.pack_start(
            self.create_information_box(_('Build:'),
                                        self._model.get_build_number()),
            False, True, 0)

        box_software.pack_start(
            self.create_information_box(_('Sugar:'),
                                        config.version),
            False, True, 0)

        box_software.pack_start(
            self.create_information_box(_('Firmware:'),
                                        self._model.get_firmware_number()),
            False, True, 0)

        box_software.pack_start(
            self.create_information_box(_('Wireless Firmware:'),
                                        self._model.get_wireless_firmware()),
            False, True, 0)

        days_from_last_update = self._model.days_from_last_update()
        if days_from_last_update >= 0:
            if days_from_last_update > 0:
                msg = _('%d days ago') % days_from_last_update
            else:
                msg = _('Today')

            box_software.pack_start(
                self.create_information_box(_('Last system update:'), msg),
                False, True, 0)

        self._vbox.pack_start(box_software, False, True, 0)
        box_software.show()

    def _setup_copyright(self):
        separator_copyright = Gtk.HSeparator()
        self._vbox.pack_start(separator_copyright, False, True, 0)
        separator_copyright.show()

        label_copyright = Gtk.Label(label=_('Copyright and License'))
        label_copyright.set_alignment(0, 0)
        self._vbox.pack_start(label_copyright, False, True, 0)
        label_copyright.show()
        vbox_copyright = Gtk.VBox()
        vbox_copyright.set_border_width(style.DEFAULT_SPACING * 2)
        vbox_copyright.set_spacing(style.DEFAULT_SPACING)

        copyright_text = '© 2006-2016 One Laptop per Child Association Inc,' \
                         ' Sugar Labs Inc, Red Hat Inc, Collabora Ltd and' \
                         ' Contributors.'
        label_copyright = Gtk.Label(label=copyright_text)
        label_copyright.set_alignment(0, 0)
        label_copyright.set_size_request(Gdk.Screen.width() / 2, -1)
        label_copyright.set_line_wrap(True)
        label_copyright.show()
        vbox_copyright.pack_start(label_copyright, False, True, 0)

        # TRANS: The word "Sugar" should not be translated.
        info_text = _('Sugar is the graphical user interface that you are'
                      ' looking at. Sugar is free software, covered by the'
                      ' GNU General Public License, and you are welcome to'
                      ' change it and/or distribute copies of it under'
                      ' certain conditions described therein.')
        label_info = Gtk.Label(label=info_text)
        label_info.set_alignment(0, 0)
        label_info.set_max_width_chars(80)
        label_info.set_line_wrap(True)
        label_info.set_size_request(Gdk.Screen.width() / 2, -1)
        label_info.show()
        vbox_copyright.pack_start(label_info, False, True, 0)

        expander = Gtk.Expander(label=_('Full license:'))
        expander.connect('notify::expanded', self.license_expander_cb)
        expander.show()
        vbox_copyright.pack_start(expander, False, True, 0)

        # display secondary licenses, if any
        for license_text in self._model.get_secondary_licenses():
            label_license = Gtk.Label(label=license_text)
            label_license.set_alignment(0, 0)
            label_license.set_line_wrap(True)
            label_license.set_size_request(Gdk.Screen.width() / 2, -1)
            label_license.show()

            separator = Gtk.HSeparator()
            vbox_copyright.pack_start(separator, False, True, 0)
            separator.show()
            vbox_copyright.pack_start(label_license, False, True, 0)

        self._vbox.pack_start(vbox_copyright, True, True, 0)
        vbox_copyright.show()

    def license_expander_cb(self, expander, param_spec):
        # load/destroy the license viewer on-demand, to avoid storing the
        # GPL in memory at all times
        if expander.get_expanded():
            view_license = Gtk.TextView()
            view_license.set_editable(False)
            view_license.get_buffer().set_text(self._model.get_license())
            fd = Pango.FontDescription('Monospace')
            view_license.modify_font(fd)
            view_license.show()
            expander.add(view_license)
        else:
            expander.get_child().destroy()
