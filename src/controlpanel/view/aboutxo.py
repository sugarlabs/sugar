import re
import os
import gtk
import gettext
import logging
_ = lambda msg: gettext.dgettext('sugar', msg)

from sugar.graphics import style

from controlpanel.detailview import DetailView

ICON = 'module-about_my_xo'
TITLE = _('About my XO')

class Aboutxo(DetailView):
    def __init__(self, model=None, alerts=None):
        DetailView.__init__(self)

        self.set_border_width(style.DEFAULT_SPACING * 2)
        self.set_spacing(style.DEFAULT_SPACING)
        not_available = _('Not available')
        group = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)

        separator_identity = gtk.HSeparator()
        self.pack_start(separator_identity, expand=False)
        separator_identity.show()
        label_identity = gtk.Label(_('Identity'))
        label_identity.set_alignment(0, 0)
        self.pack_start(label_identity, expand=False)
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
        group.add_widget(label_serial)
        label_serial.show()
        serial_no = self._read_file('/ofw/serial-number')
        if serial_no is None:
            serial_no = not_available
        label_serial_no = gtk.Label(serial_no)
        label_serial_no.set_alignment(0, 0)
        box_identity.pack_start(label_serial_no, expand=False)
        label_serial_no.show()
        vbox_identity.pack_start(box_identity, expand=False)
        box_identity.show()
        self.pack_start(vbox_identity, expand=False)
        vbox_identity.show()

        separator_software = gtk.HSeparator()
        self.pack_start(separator_software, expand=False)
        separator_software.show()
        label_software = gtk.Label(_('Software'))
        label_software.set_alignment(0, 0)
        self.pack_start(label_software, expand=False)
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
        group.add_widget(label_build)
        label_build.show()
        build_no = self._read_file('/boot/olpc_build')
        if build_no is None:
            build_no = not_available
        label_build_no = gtk.Label(build_no)
        label_build_no.set_alignment(0, 0)
        box_build.pack_start(label_build_no, expand=False)
        label_build_no.show()
        box_software.pack_start(box_build, expand=False)
        box_build.show()

        box_firmware = gtk.HBox(spacing=style.DEFAULT_SPACING)
        label_firmware = gtk.Label(_('Firmware:'))
        label_firmware.set_alignment(1, 0)
        label_firmware.modify_fg(gtk.STATE_NORMAL, 
                              style.COLOR_SELECTION_GREY.get_gdk_color())
        box_firmware.pack_start(label_firmware, expand=False)
        group.add_widget(label_firmware)
        label_firmware.show()
        firmware_no = self._read_file('/ofw/openprom/model')
        if firmware_no is None:
            firmware_no = not_available
        else:
            firmware_no = re.split(" +", firmware_no)
            if len(firmware_no) == 3:
                firmware_no = firmware_no[1]
        label_firmware_no = gtk.Label(firmware_no)
        label_firmware_no.set_alignment(0, 0)
        box_firmware.pack_start(label_firmware_no, expand=False)
        label_firmware_no.show()
        box_software.pack_start(box_firmware, expand=False)
        box_firmware.show()
        self.pack_start(box_software, expand=False)
        box_software.show()

    def _read_file(self, path):
        if os.access(path, os.R_OK) == 0:
            logging.error('read_file() No such file or directory: %s', path)
            return None

        fd = open(path, 'r')
        value = fd.read()
        fd.close()
        if value:
            value = value.strip('\n')
            return value
        else:
            logging.error('read_file() No information in file or directory: %s'
                          , path)
            return None
