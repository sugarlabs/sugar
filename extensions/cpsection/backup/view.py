# Copyright (C) 2013, SugarLabs
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import logging
from gettext import gettext as _

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject

from sugar3.graphics.icon import Icon
from sugar3.graphics import style

from jarabe.controlpanel.sectionview import SectionView

from backupmanager import BackupManager
from backupmanager import OPERATION_BACKUP, OPERATION_RESTORE
from backends.backend_tools import PreConditionsError
from backends.backend_tools import PreConditionsChoose


class BackupView(SectionView):
    __gtype_name__ = 'SugarBackupWindow'

    def __init__(self, model, alerts=None):
        SectionView.__init__(self)
        self.needs_restart = False

        # add the initial panel
        self.set_canvas(SelectBackupRestorePanel(self))
        self.grab_focus()
        self.show_all()
        self.manager = BackupManager()

    def set_canvas(self, canvas):
        if len(self.get_children()) > 0:
            self.remove(self.get_children()[0])
        if canvas:
            logging.error('adding canvas %s', canvas)
            self.add(canvas)

    def undo(self):
        if self.get_children()[0].__class__ == OperationPanel:
            operation_panel = self.get_children()[0]
            if operation_panel._operator is not None:
                operation_panel._operator.cancel()


class BigButton(Gtk.Button):

    def __init__(self, _icon_name, label):
        Gtk.Button.__init__(self)
        _icon = Icon(icon_name=_icon_name,
                     pixel_size=style.MEDIUM_ICON_SIZE)
        self.set_label(label)
        self.set_image(_icon)
        self.set_image_position(Gtk.PositionType.TOP)

        theme = "GtkButton {padding: %spx;}" % (style.DEFAULT_SPACING * 2)
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(theme)
        style_context = self.get_style_context()
        style_context.add_provider(css_provider,
                                   Gtk.STYLE_PROVIDER_PRIORITY_USER)


class SelectBackupRestorePanel(Gtk.VBox):

    def __init__(self, view):
        Gtk.VBox.__init__(self)

        self._view = view
        hbox = Gtk.HBox()

        self.backup_btn = BigButton(
            'backup', _('Make a safe copy of the content of your Journal'))
        hbox.pack_start(self.backup_btn, False, False, style.DEFAULT_SPACING)
        self.backup_btn.connect('clicked', self.__backup_clicked_cb)

        self.restore_btn = BigButton(
            'restore', _('Restore a security copy into your Journal'))
        hbox.pack_start(self.restore_btn, False, False, style.DEFAULT_SPACING)
        self.restore_btn.connect('clicked', self.__restore_clicked_cb)
        hbox.set_valign(Gtk.Align.CENTER)
        hbox.set_halign(Gtk.Align.CENTER)
        self.add(hbox)
        self.show_all()

    def __backup_clicked_cb(self, button):
        operation_panel = OperationPanel(OPERATION_BACKUP, self._view)
        self._view.set_canvas(operation_panel)

    def __restore_clicked_cb(self, button):
        operation_panel = OperationPanel(OPERATION_RESTORE, self._view)
        self._view.set_canvas(operation_panel)


class OperationPanel(Gtk.Grid):

    def __init__(self, operation, view):
        Gtk.Grid.__init__(self)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_row_spacing(style.DEFAULT_SPACING)
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)

        self._view = view
        self._operation = operation
        self._backend = None

        _icon = Icon(icon_name='backup-%s' % operation,
                     pixel_size=style.XLARGE_ICON_SIZE)
        self.add(_icon)
        _icon.show()

        self._message_label = Gtk.Label()
        self.add(self._message_label)
        self._message_label.show()

        self._options_combo = Gtk.ComboBox()
        cell = Gtk.CellRendererText()
        self._options_combo.pack_start(cell, True)
        self._options_combo.add_attribute(cell, 'text', 0)
        self.add(self._options_combo)

        self._progress_bar = Gtk.ProgressBar()
        self.add(self._progress_bar)
        self._progress_bar.set_size_request(
            Gdk.Screen.width() - style.GRID_CELL_SIZE * 6, -1)

        self._confirm_restore_chkbtn = Gtk.CheckButton()
        self.add(self._confirm_restore_chkbtn)

        self._continue_btn = Gtk.Button(_('Continue'))
        self.add(self._continue_btn)
        self._continue_btn_handler_id = 0

        self.show()

        # check if there are activities running
        # and request close them if any.
        if self._view.manager.need_stop_activities():
            self._message_label.set_text(
                _('Please close all the activities, and start again'))

        # check the backend availables, if there are more than one
        # show to the user to select one
        if len(self._view.manager.get_backends()) > 1:
            if operation == OPERATION_BACKUP:
                message = _('Select where you want create your backup')
            if operation == OPERATION_RESTORE:
                message = _('Select where you want retrive your restore')
            combo_options = []
            for backend in self._view.manager.get_backends():
                option = {}
                option['description'] = backend.get_name()
                option['value'] = backend
                combo_options.append(option)

            self._ask_options(message, combo_options, self._select_backend)
        else:
            self._backend = self._view.manager.get_backends()[0]
            GObject.idle_add(self._start_operation)

    def _ask_options(self, message, options, continue_cb):
        """
        message: str
        options: dictionary
        continue_cb: the call back method to assign to the continue button
                     clicked event.
        """
        self._message_label.set_text(message)
        options_store = Gtk.ListStore(GObject.TYPE_STRING,
                                      GObject.TYPE_PYOBJECT)
        for option in options:
            options_store.append([option['description'], option['value']])
        self._options_combo.set_model(options_store)

        self._options_combo.show()

        if self._continue_btn_handler_id != 0:
            self._continue_btn.disconnect(self._continue_btn_handler_id)

        self._continue_btn_handler_id = self._continue_btn.connect(
            'clicked', continue_cb)
        self._continue_btn.set_label(_('Continue'))
        self._continue_btn.show()

    def _show_error_message(self, message):
        self._message_label.set_text(message)
        self._options_combo.hide()
        self._continue_btn.set_label(_('Retry'))
        self._continue_btn.show()
        if self._continue_btn_handler_id != 0:
            self._continue_btn.disconnect(self._continue_btn_handler_id)
        self._continue_btn_handler_id = self._continue_btn.connect(
            'clicked', self.__retry_cb)

    def _select_backend(self, button):
        itererator = self._options_combo.get_active_iter()
        model = self._options_combo.get_model()
        self._backend = model.get(itererator, 1)[0]
        self._start_operation()

    def _start_operation(self):
        logging.error('Starting operation %s with backend %s',
                      self._operation, self._backend.get_name())

        if self._operation == OPERATION_BACKUP:
            self._operator = self._backend.get_backup()

        if self._operation == OPERATION_RESTORE:
            self._operator = self._backend.get_restore()

        self._continue_operation()

    def _continue_operation(self, options={}):
        need_more_information = True
        try:
            self._operator.verify_preconditions(options)
            need_more_information = False
        except PreConditionsError as e:
            self._show_error_message(str(e))
        except PreConditionsChoose as e:
            self._backend_parameter = e.options['parameter']
            self._ask_options(str(e), e.options['options'],
                              self._assign_parameter_backend)
        if not need_more_information:
            if self._operation == OPERATION_BACKUP:
                logging.error('Starting backup...')
                self._message_label.set_text(
                    _('Starting backup...'))
                GObject.idle_add(self._internal_start_operation)

            if self._operation == OPERATION_RESTORE:
                # The restore is potentially dangerous
                # because will destroy all the information in the journal
                # ask for a confirmation before doing the restore
                self._request_restore_confirmation()

    def _request_restore_confirmation(self):
        self._message_label.set_text(_('Please confirm'))
        self._confirm_restore_chkbtn.set_label(
            _('I want remove all the content in my Journal,'
              ' and restore the information from the selected checkpoint'))
        self._confirm_restore_chkbtn.show()
        self._options_combo.hide()
        self._continue_btn.set_label(_('Confirm'))
        if self._continue_btn_handler_id != 0:
            self._continue_btn.disconnect(self._continue_btn_handler_id)
        self._continue_btn_handler_id = self._continue_btn.connect(
            'clicked', self.__confirm_restore_cb)

    def __confirm_restore_cb(self, button):
        if self._confirm_restore_chkbtn.get_active():
            self._view.props.is_cancellable = False
            self._confirm_restore_chkbtn.hide()
            self._continue_btn.hide()
            self._message_label.set_text('')
            self._internal_start_operation()
            self._view.needs_restart = True

    def _internal_start_operation(self):
        self._operator.connect('started', self.__operation_started_cb)
        self._operator.connect('progress', self.__operation_progress_cb)
        self._operator.connect('finished', self.__operation_finished_cb)
        self._operator.connect('cancelled', self.__operation_cancelled_cb)

        # disable the accept button until the operation finish
        self._view.props.is_valid = False

        GObject.idle_add(self._operator.start)

    def __retry_cb(self, button):
        self._start_operation()

    def _assign_parameter_backend(self, button):
        itererator = self._options_combo.get_active_iter()
        model = self._options_combo.get_model()
        value = model.get(itererator, 1)[0]
        options = {self._backend_parameter: value}
        self._continue_operation(options)

    def __operation_started_cb(self, backend):
        self._message_label.set_text(_('Operation started'))
        self._options_combo.hide()
        self._continue_btn.hide()
        self._progress_bar.set_fraction(0.0)
        self._progress_bar.show()

    def __operation_progress_cb(self, backend, fraction):
        self._progress_bar.set_fraction(fraction)

    def __operation_finished_cb(self, backend):
        self._progress_bar.set_fraction(1.0)
        if self._operation == OPERATION_BACKUP:
            self._message_label.set_text(_('Backup finished successfully'))
        if self._operation == OPERATION_RESTORE:
            self._message_label.set_text(_('Restore realized successfully.'))
        self._view.props.is_valid = True

    def __operation_cancelled_cb(self, backend):
        self._view.props.is_valid = True
