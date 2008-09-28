# coding=utf-8
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

import config
from sugar.graphics import style

from jarabe.controlpanel.sectionview import SectionView

class AboutXO(SectionView):
    def __init__(self, model, alerts=None):
        SectionView.__init__(self)

        self._model = model

        self.set_border_width(style.DEFAULT_SPACING * 2)
        self.set_spacing(style.DEFAULT_SPACING)

        self._group = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)

        scrollwindow = gtk.ScrolledWindow()
        scrollwindow.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.pack_start(scrollwindow, expand=True)
        scrollwindow.show()

        self._vbox = gtk.VBox()
        scrollwindow.add_with_viewport(self._vbox)
        self._vbox.show()

        self._setup_identity()
        self._setup_software()
        self._setup_copyright()

    def _setup_identity(self):
        separator_identity = gtk.HSeparator()
        self._vbox.pack_start(separator_identity, expand=False)
        separator_identity.show()

        label_identity = gtk.Label(_('Identity'))
        label_identity.set_alignment(0, 0)
        self._vbox.pack_start(label_identity, expand=False)
        label_identity.show()
        vbox_identity = gtk.VBox()
        vbox_identity.set_border_width(style.DEFAULT_SPACING * 2)
        vbox_identity.set_spacing(style.DEFAULT_SPACING)

        box_identity = gtk.HBox(spacing=style.DEFAULT_SPACING)
        label_serial = gtk.Label(_('Serial Number:'))
        label_serial.set_alignment(1, 0)
        label_serial.modify_fg(gtk.STATE_NORMAL, 
                               style.COLOR_SELECTION_GREY.get_gdk_color())
        box_identity.pack_start(label_serial, expand=False)
        self._group.add_widget(label_serial)
        label_serial.show()
        label_serial_no = gtk.Label(self._model.get_serial_number())
        label_serial_no.set_alignment(0, 0)
        box_identity.pack_start(label_serial_no, expand=False)
        label_serial_no.show()
        vbox_identity.pack_start(box_identity, expand=False)
        box_identity.show()

        self._vbox.pack_start(vbox_identity, expand=False)
        vbox_identity.show()
    

    def _setup_software(self):   
        separator_software = gtk.HSeparator()
        self._vbox.pack_start(separator_software, expand=False)
        separator_software.show()

        label_software = gtk.Label(_('Software'))
        label_software.set_alignment(0, 0)
        self._vbox.pack_start(label_software, expand=False)
        label_software.show()
        box_software = gtk.VBox()
        box_software.set_border_width(style.DEFAULT_SPACING * 2)
        box_software.set_spacing(style.DEFAULT_SPACING)

        box_build = gtk.HBox(spacing=style.DEFAULT_SPACING)
        label_build = gtk.Label(_('Build:'))
        label_build.set_alignment(1, 0)
        label_build.modify_fg(gtk.STATE_NORMAL, 
                              style.COLOR_SELECTION_GREY.get_gdk_color())
        box_build.pack_start(label_build, expand=False)
        self._group.add_widget(label_build)
        label_build.show()
        label_build_no = gtk.Label(self._model.get_build_number())
        label_build_no.set_alignment(0, 0)
        box_build.pack_start(label_build_no, expand=False)
        label_build_no.show()
        box_software.pack_start(box_build, expand=False)
        box_build.show()

        box_sugar = gtk.HBox(spacing=style.DEFAULT_SPACING)
        label_sugar = gtk.Label(_('Sugar:'))
        label_sugar.set_alignment(1, 0)
        label_sugar.modify_fg(gtk.STATE_NORMAL,
                              style.COLOR_SELECTION_GREY.get_gdk_color())
        box_sugar.pack_start(label_sugar, expand=False)
        self._group.add_widget(label_sugar)
        label_sugar.show()
        label_sugar_ver = gtk.Label(config.version)
        label_sugar_ver.set_alignment(0, 0)
        box_sugar.pack_start(label_sugar_ver, expand=False)
        label_sugar_ver.show()
        box_software.pack_start(box_sugar, expand=False)
        box_sugar.show()

        box_firmware = gtk.HBox(spacing=style.DEFAULT_SPACING)
        label_firmware = gtk.Label(_('Firmware:'))
        label_firmware.set_alignment(1, 0)
        label_firmware.modify_fg(gtk.STATE_NORMAL, 
                              style.COLOR_SELECTION_GREY.get_gdk_color())
        box_firmware.pack_start(label_firmware, expand=False)
        self._group.add_widget(label_firmware)
        label_firmware.show()
        label_firmware_no = gtk.Label(self._model.get_firmware_number())
        label_firmware_no.set_alignment(0, 0)
        box_firmware.pack_start(label_firmware_no, expand=False)
        label_firmware_no.show()
        box_software.pack_start(box_firmware, expand=False)
        box_firmware.show()

        self._vbox.pack_start(box_software, expand=False)
        box_software.show()

    def _setup_copyright(self):
        separator_copyright = gtk.HSeparator()
        self._vbox.pack_start(separator_copyright, expand=False)
        separator_copyright.show()

        label_copyright = gtk.Label(_('Copyright and License'))
        label_copyright.set_alignment(0, 0)
        self._vbox.pack_start(label_copyright, expand=False)
        label_copyright.show()
        vbox_copyright = gtk.VBox()
        vbox_copyright.set_border_width(style.DEFAULT_SPACING * 2)
        vbox_copyright.set_spacing(style.DEFAULT_SPACING)

        label_copyright = gtk.Label(_("© 2008 One Laptop per Child "
                                      "Association Inc; Red Hat Inc; "
                                      "and Contributors."))
        label_copyright.set_alignment(0, 0)
        label_copyright.show()
        vbox_copyright.pack_start(label_copyright, expand=False)

        label_info = gtk.Label(_("Sugar is the graphical user interface that "
                                 "you are looking at. Sugar is free software, "
                                 "covered by the GNU General Public License, "
                                 "and you are welcome to change it and/or "
                                 "distribute copies of it under certain "
                                 "conditions described therein."))
        label_info.set_alignment(0, 0)
        label_info.set_line_wrap(True)
        label_info.set_size_request(gtk.gdk.screen_width() / 2, -1)
        label_info.show()
        vbox_copyright.pack_start(label_info, expand=False)

        expander = gtk.Expander(_("Full license:"))
        expander.connect("notify::expanded", self.license_expander_cb)
        expander.show()
        vbox_copyright.pack_start(expander, expand=True)

        self._vbox.pack_start(vbox_copyright, expand=True)
        vbox_copyright.show()

    def license_expander_cb(self, expander, param_spec):
        # load/destroy the license viewer on-demand, to avoid storing the
        # GPL in memory at all times
        if expander.get_expanded():
            view_license = gtk.TextView()
            view_license.set_editable(False)
            view_license.get_buffer().set_text(self._model.get_license())
            view_license.show()
            expander.add(view_license)
        else:
            expander.get_child().destroy()
