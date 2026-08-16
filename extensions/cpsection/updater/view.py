# Copyright (C) 2008, One Laptop Per Child
# Copyright (C) 2009, Tomeu Vizoso
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
from gettext import ngettext
import locale
import logging

from gi.repository import GLib
from gi.repository import Gtk

from sugar4.graphics import style
from sugar4.graphics.icon import Icon, CellRendererIcon

from jarabe.controlpanel.sectionview import SectionView
from jarabe.model.update import updater
from jarabe.model import bundleregistry

_DEBUG_VIEW_ALL = True


class ActivityUpdater(SectionView):

    def __init__(self, model, alerts):
        SectionView.__init__(self)

        self._model = updater.get_instance()
        self._id_progresss = self._model.connect('progress',
                                                 self.__progress_cb)
        self._id_updates = self._model.connect('updates-available',
                                               self.__updates_available_cb)
        self._id_error = self._model.connect('error',
                                             self.__error_cb)
        self._id_finished = self._model.connect('finished',
                                                self.__finished_cb)

        self.set_spacing(style.DEFAULT_SPACING)
        self.set_margin_start(style.DEFAULT_SPACING * 2)
        self.set_margin_end(style.DEFAULT_SPACING * 2)
        self.set_margin_top(style.DEFAULT_SPACING * 2)
        self.set_margin_bottom(style.DEFAULT_SPACING * 2)

        self._top_label = Gtk.Label()
        self._top_label.set_wrap(True)
        self._top_label.set_justify(Gtk.Justification.LEFT)
        self._top_label.props.xalign = 0
        self.append(self._top_label)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.append(separator)

        self._bottom_label = Gtk.Label()
        self._bottom_label.set_wrap(True)
        self._bottom_label.set_justify(Gtk.Justification.LEFT)
        self._bottom_label.props.xalign = 0
        self._bottom_label.set_markup(
            _('Software updates correct errors, eliminate security '
              'vulnerabilities, and provide new features.'))
        self.append(self._bottom_label)

        self._update_box = None
        self._progress_pane = None

        state = self._model.get_state()
        if state in (updater.STATE_IDLE, updater.STATE_CHECKED):
            self._refresh()
        elif state in (updater.STATE_CHECKING, updater.STATE_DOWNLOADING,
                       updater.STATE_UPDATING):
            self._switch_to_progress_pane()
            self._progress_pane.set_message(_('Update in progress...'))
        self.connect('unrealize', self.__destroy_cb)

    def __destroy_cb(self, widget):
        self._model.disconnect(self._id_progresss)
        self._model.disconnect(self._id_updates)
        self._model.disconnect(self._id_error)
        self._model.disconnect(self._id_finished)
        self._model.clean()

    def _switch_to_update_box(self, updates):
        if self._update_box and self._update_box.get_parent() == self:
            return

        if self._progress_pane and self._progress_pane.get_parent() == self:
            self.remove(self._progress_pane)
            self._progress_pane = None

        if self._update_box is None:
            self._update_box = UpdateBox(updates)
            self._update_box.refresh_button.connect(
                'clicked',
                self.__refresh_button_clicked_cb)
            self._update_box.install_button.connect(
                'clicked',
                self.__install_button_clicked_cb)

        self.append(self._update_box)
        self._update_box.set_hexpand(True)
        self._update_box.set_vexpand(True)

    def _switch_to_progress_pane(self):
        if self._progress_pane and self._progress_pane.get_parent() == self:
            return

        if self._model.get_state() == updater.STATE_CHECKING:
            top_message = _('Checking for updates...')
        else:
            top_message = _('Installing updates...')
        self._top_label.set_markup('<big>%s</big>' % top_message)

        if self._update_box and self._update_box.get_parent() == self:
            self.remove(self._update_box)
            self._update_box = None

        if self._progress_pane is None:
            self._progress_pane = ProgressPane()
            self._progress_pane.cancel_button.connect(
                'clicked',
                self.__cancel_button_clicked_cb)

        self.append(self._progress_pane)
        self._progress_pane.set_hexpand(True)

    def _clear_center(self):
        if self._progress_pane and self._progress_pane.get_parent() == self:
            self.remove(self._progress_pane)
            self._progress_pane = None

        if self._update_box and self._update_box.get_parent() == self:
            self.remove(self._update_box)
            self._update_box = None

    def __progress_cb(self, model, state, bundle_name, progress):
        if state == updater.STATE_CHECKING:
            if bundle_name:
                message = _('Checking %s...') % bundle_name
            else:
                message = _('Looking for updates...')
        elif state == updater.STATE_DOWNLOADING:
            message = _('Downloading %s...') % bundle_name
        elif state == updater.STATE_UPDATING:
            message = _('Updating %s...') % bundle_name

        self._switch_to_progress_pane()
        self._progress_pane.set_message(message)
        self._progress_pane.set_progress(progress)

    def __updates_available_cb(self, model, updates):
        logging.debug('ActivityUpdater.__updates_available_cb')
        available_updates = len(updates)
        if not available_updates:
            top_message = _('Your software is up-to-date')
        else:
            top_message = ngettext('You can install %s update',
                                   'You can install %s updates',
                                   available_updates)
            top_message = top_message % available_updates
            top_message = GLib.markup_escape_text(top_message)

        self._top_label.set_markup('<big>%s</big>' % top_message)

        if not available_updates:
            self._clear_center()
        else:
            self._switch_to_update_box(updates)

    def __error_cb(self, model, updates):
        logging.debug('ActivityUpdater.__error_cb')
        top_message = _('Can\'t connect to the activity server')
        self._top_label.set_markup('<big>%s</big>' % top_message)
        self._bottom_label.set_markup(
            _('Verify your connection to internet and try again, '
              'or try again later'))
        self._clear_center()

    def __refresh_button_clicked_cb(self, button):
        self._refresh()

    def _refresh(self):
        self._model.check_updates()

    def __install_button_clicked_cb(self, button):
        self._model.update(self._update_box.get_bundles_to_update())

    def __cancel_button_clicked_cb(self, button):
        self._model.cancel()

    def __finished_cb(self, model, installed_updates, failed_updates,
                      cancelled):
        num_installed = len(installed_updates)
        logging.debug('ActivityUpdater.__finished_cb')
        top_message = ngettext('%s update was installed',
                               '%s updates were installed', num_installed)
        top_message = top_message % num_installed
        top_message = GLib.markup_escape_text(top_message)
        self._top_label.set_markup('<big>%s</big>' % top_message)
        self._clear_center()

    def undo(self):
        self._model.cancel()


class ProgressPane(Gtk.Box):
    """Container which replaces the `ActivityPane` during refresh or
    install."""

    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        self.set_spacing(style.DEFAULT_PADDING)
        self.set_margin_start(style.DEFAULT_SPACING * 2)
        self.set_margin_end(style.DEFAULT_SPACING * 2)
        self.set_margin_top(style.DEFAULT_SPACING * 2)
        self.set_margin_bottom(style.DEFAULT_SPACING * 2)

        self._progress = Gtk.ProgressBar()
        self.append(self._progress)
        self._progress.set_hexpand(True)
        self._progress.set_vexpand(True)

        self._label = Gtk.Label()
        self._label.set_wrap(True)
        self._label.set_property('xalign', 0.5)

        self.append(self._label)
        self._label.set_hexpand(True)
        self._label.set_vexpand(True)

        alignment_box = Gtk.Box()
        alignment_box.set_halign(Gtk.Align.CENTER)
        alignment_box.set_valign(Gtk.Align.CENTER)
        self.append(alignment_box)
        alignment_box.set_hexpand(True)
        alignment_box.set_vexpand(True)

        self.cancel_button = Gtk.Button(label=_('Cancel'))
        alignment_box.append(self.cancel_button)

    def set_message(self, message):
        self._label.set_text(message)

    def set_progress(self, fraction):
        self._progress.props.fraction = fraction


class UpdateBox(Gtk.Box):

    def __init__(self, updates):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)

        self.set_spacing(style.DEFAULT_PADDING)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.append(scrolled_window)
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)

        self._update_list = UpdateList(updates)
        self._update_list.props.model.connect('row-changed',
                                              self.__row_changed_cb)
        scrolled_window.set_child(self._update_list)

        bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        bottom_box.set_spacing(style.DEFAULT_SPACING)
        self.append(bottom_box)

        self._size_label = Gtk.Label()
        self._size_label.props.xalign = 0
        self._size_label.set_justify(Gtk.Justification.LEFT)
        bottom_box.append(self._size_label)
        self._size_label.set_hexpand(True)
        self._size_label.set_vexpand(True)

        self.refresh_button = Gtk.Button(label=_('Refresh'))
        bottom_box.append(self.refresh_button)

        self.install_button = Gtk.Button()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=style.DEFAULT_SPACING)
        box.append(Icon(icon_name='emblem-downloads', pixel_size=style.SMALL_ICON_SIZE))
        box.append(Gtk.Label(label=_('Install selected')))
        self.install_button.set_child(box)
        bottom_box.append(self.install_button)

        self._update_total_size_label()

    def __row_changed_cb(self, list_model, path, iterator):
        self._update_total_size_label()
        self._update_install_button()

    def _update_total_size_label(self):
        total_size = 0
        for row in self._update_list.props.model:
            if row[UpdateListModel.SELECTED]:
                total_size += row[UpdateListModel.SIZE]

        markup = _('Download size: %s') % _format_size(total_size)
        self._size_label.set_markup(markup)

    def _update_install_button(self):
        for row in self._update_list.props.model:
            if row[UpdateListModel.SELECTED]:
                self.install_button.props.sensitive = True
                return
        self.install_button.props.sensitive = False

    def get_bundles_to_update(self):
        bundles_to_update = []
        for row in self._update_list.props.model:
            if row[UpdateListModel.SELECTED]:
                bundles_to_update.append(row[UpdateListModel.BUNDLE_ID])
        return bundles_to_update


class UpdateList(Gtk.TreeView):

    def __init__(self, updates):
        list_model = UpdateListModel(updates)
        Gtk.TreeView.__init__(self, model=list_model)

        self.set_reorderable(False)
        self.set_enable_search(False)
        self.set_headers_visible(False)

        toggle_renderer = Gtk.CellRendererToggle()
        toggle_renderer.props.activatable = True
        toggle_renderer.props.xpad = style.DEFAULT_PADDING
        toggle_renderer.connect('toggled', self.__toggled_cb)

        toggle_column = Gtk.TreeViewColumn()
        toggle_column.pack_start(toggle_renderer, True)
        toggle_column.add_attribute(toggle_renderer, 'active',
                                    UpdateListModel.SELECTED)
        self.append_column(toggle_column)

        icon_renderer = CellRendererIcon()
        icon_renderer.props.width = style.STANDARD_ICON_SIZE
        icon_renderer.props.height = style.STANDARD_ICON_SIZE
        icon_renderer.props.size = style.STANDARD_ICON_SIZE
        icon_renderer.props.xpad = style.DEFAULT_PADDING
        icon_renderer.props.ypad = style.DEFAULT_PADDING
        icon_renderer.props.stroke_color = style.COLOR_TOOLBAR_GREY.get_svg()
        icon_renderer.props.fill_color = style.COLOR_TRANSPARENT.get_svg()

        icon_column = Gtk.TreeViewColumn()
        icon_column.pack_start(icon_renderer, True)
        icon_column.add_attribute(icon_renderer, 'file-name',
                                  UpdateListModel.ICON_FILE_NAME)
        self.append_column(icon_column)

        text_renderer = Gtk.CellRendererText()

        description_column = Gtk.TreeViewColumn()
        description_column.pack_start(text_renderer, True)
        description_column.add_attribute(text_renderer, 'markup',
                                         UpdateListModel.DESCRIPTION)
        self.append_column(description_column)

    def __toggled_cb(self, cell_renderer, path):
        row = self.props.model[path]
        row[UpdateListModel.SELECTED] = not row[UpdateListModel.SELECTED]


class UpdateListModel(Gtk.ListStore):

    BUNDLE_ID = 0
    SELECTED = 1
    ICON_FILE_NAME = 2
    DESCRIPTION = 3
    SIZE = 4

    def __init__(self, updates):
        Gtk.ListStore.__init__(self, str, bool, str, str, int)
        registry = bundleregistry.get_registry()

        for bundle_update in updates:
            installed = registry.get_bundle(bundle_update.bundle_id)
            row = [None] * 5
            row[self.BUNDLE_ID] = bundle_update.bundle_id
            row[self.SELECTED] = not bundle_update.optional
            if installed:
                row[self.ICON_FILE_NAME] = installed.get_icon()
            else:
                if bundle_update.icon_file_name is not None:
                    row[self.ICON_FILE_NAME] = bundle_update.icon_file_name

            if installed:
                details = _('From version %(current)s to %(new)s (Size: '
                            '%(size)s)')
                details = details % \
                    {'current': installed.get_activity_version(),
                     'new': bundle_update.version,
                     'size': _format_size(bundle_update.size)}
            else:
                details = _('Version %(version)s (Size: %(size)s)')
                details = details % \
                    {'version': bundle_update.version,
                     'size': _format_size(bundle_update.size)}

            row[self.DESCRIPTION] = '<b>%s</b>\n%s' % \
                (bundle_update.name, details)

            row[self.SIZE] = bundle_update.size

            self.append(row)


def _format_size(size):
    """Convert a given size in bytes to a nicer better readable unit"""
    if size == 0:
        # TRANS: download size is 0
        return _('None')
    if size < 1024:
        # TRANS: download size of very small updates
        return _('1 KiB')
    if size < 1024 * 1024:
        # TRANS: download size of small updates, e.g. '250 KiB'
        return locale.format_string(_('%.0f KiB'), size / 1024.0)
    # TRANS: download size of updates, e.g. '2.3 MiB'
    return locale.format_string(_('%.1f MiB'), size / 1024.0 / 1024)
