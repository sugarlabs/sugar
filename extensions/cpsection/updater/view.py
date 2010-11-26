# Copyright (C) 2008, One Laptop Per Child
# Copyright (C) 2009, Tomeu Vizoso
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

from gettext import gettext as _
from gettext import ngettext
import locale
import logging

import gobject
import gtk

from sugar.graphics import style
from sugar.graphics.icon import Icon, CellRendererIcon

from jarabe.controlpanel.sectionview import SectionView

from model import UpdateModel

_DEBUG_VIEW_ALL = True


class ActivityUpdater(SectionView):

    def __init__(self, model, alerts):
        SectionView.__init__(self)

        self._model = UpdateModel()
        self._model.connect('progress', self.__progress_cb)

        self.set_spacing(style.DEFAULT_SPACING)
        self.set_border_width(style.DEFAULT_SPACING * 2)

        self._top_label = gtk.Label()
        self._top_label.set_line_wrap(True)
        self._top_label.set_justify(gtk.JUSTIFY_LEFT)
        self._top_label.props.xalign = 0
        self.pack_start(self._top_label, expand=False)
        self._top_label.show()

        separator = gtk.HSeparator()
        self.pack_start(separator, expand=False)
        separator.show()

        bottom_label = gtk.Label()
        bottom_label.set_line_wrap(True)
        bottom_label.set_justify(gtk.JUSTIFY_LEFT)
        bottom_label.props.xalign = 0
        bottom_label.set_markup(
                _('Software updates correct errors, eliminate security ' \
                  'vulnerabilities, and provide new features.'))
        self.pack_start(bottom_label, expand=False)
        bottom_label.show()

        self._update_box = None
        self._progress_pane = None

        self._refresh()

    def _switch_to_update_box(self):
        if self._update_box in self.get_children():
            return

        if self._progress_pane in self.get_children():
            self.remove(self._progress_pane)
            self._progress_pane = None

        if self._update_box is None:
            self._update_box = UpdateBox(self._model)
            self._update_box.refresh_button.connect('clicked',
                    self.__refresh_button_clicked_cb)
            self._update_box.install_button.connect('clicked',
                    self.__install_button_clicked_cb)

        self.pack_start(self._update_box, expand=True, fill=True)
        self._update_box.show()

    def _switch_to_progress_pane(self):
        if self._progress_pane in self.get_children():
            return

        if self._update_box in self.get_children():
            self.remove(self._update_box)
            self._update_box = None

        if self._progress_pane is None:
            self._progress_pane = ProgressPane()
            self._progress_pane.cancel_button.connect('clicked',
                    self.__cancel_button_clicked_cb)

        self.pack_start(self._progress_pane, expand=True, fill=False)
        self._progress_pane.show()

    def _clear_center(self):
        if self._progress_pane in self.get_children():
            self.remove(self._progress_pane)
            self._progress_pane = None

        if self._update_box in self.get_children():
            self.remove(self._update_box)
            self._update_box = None

    def __progress_cb(self, model, action, bundle_name, current, total):
        if current == total and action == UpdateModel.ACTION_CHECKING:
            self._finished_checking()
            return
        elif current == total:
            self._finished_updating(int(current))
            return

        if action == UpdateModel.ACTION_CHECKING:
            message = _('Checking %s...') % bundle_name
        elif action == UpdateModel.ACTION_DOWNLOADING:
            message = _('Downloading %s...') % bundle_name
        elif action == UpdateModel.ACTION_UPDATING:
            message = _('Updating %s...') % bundle_name

        self._switch_to_progress_pane()
        self._progress_pane.set_message(message)
        self._progress_pane.set_progress(current / float(total))

    def _finished_checking(self):
        logging.debug('ActivityUpdater._finished_checking')
        available_updates = len(self._model.updates)
        if not available_updates:
            top_message = _('Your software is up-to-date')
        else:
            top_message = ngettext('You can install %s update',
                                   'You can install %s updates',
                                   available_updates)
            top_message = top_message % available_updates
            top_message = gobject.markup_escape_text(top_message)

        self._top_label.set_markup('<big>%s</big>' % top_message)

        if not available_updates:
            self._clear_center()
        else:
            self._switch_to_update_box()
            self._update_box.refresh()

    def __refresh_button_clicked_cb(self, button):
        self._refresh()

    def _refresh(self):
        top_message = _('Checking for updates...')
        self._top_label.set_markup('<big>%s</big>' % top_message)
        self._model.check_updates()

    def __install_button_clicked_cb(self, button):
        text = '<big>%s</big>' % _('Installing updates...')
        self._top_label.set_markup(text)
        self._model.update(self._update_box.get_bundles_to_update())

    def __cancel_button_clicked_cb(self, button):
        self._model.cancel()

    def _finished_updating(self, installed_updates):
        logging.debug('ActivityUpdater._finished_updating')
        top_message = ngettext('%s update was installed',
                               '%s updates were installed', installed_updates)
        top_message = top_message % installed_updates
        top_message = gobject.markup_escape_text(top_message)
        self._top_label.set_markup('<big>%s</big>' % top_message)
        self._clear_center()

    def undo(self):
        self._model.cancel()


class ProgressPane(gtk.VBox):
    """Container which replaces the `ActivityPane` during refresh or
    install."""

    def __init__(self):
        gtk.VBox.__init__(self)
        self.set_spacing(style.DEFAULT_PADDING)
        self.set_border_width(style.DEFAULT_SPACING * 2)

        self._progress = gtk.ProgressBar()
        self.pack_start(self._progress)
        self._progress.show()

        self._label = gtk.Label()
        self._label.set_line_wrap(True)
        self._label.set_property('xalign', 0.5)
        self._label.modify_fg(gtk.STATE_NORMAL,
                              style.COLOR_BUTTON_GREY.get_gdk_color())
        self.pack_start(self._label)
        self._label.show()

        alignment_box = gtk.Alignment(xalign=0.5, yalign=0.5)
        self.pack_start(alignment_box)
        alignment_box.show()

        self.cancel_button = gtk.Button(stock=gtk.STOCK_CANCEL)
        alignment_box.add(self.cancel_button)
        self.cancel_button.show()

    def set_message(self, message):
        self._label.set_text(message)

    def set_progress(self, fraction):
        self._progress.props.fraction = fraction


class UpdateBox(gtk.VBox):

    def __init__(self, model):
        gtk.VBox.__init__(self)

        self._model = model

        self.set_spacing(style.DEFAULT_PADDING)

        scrolled_window = gtk.ScrolledWindow()
        scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.pack_start(scrolled_window)
        scrolled_window.show()

        self._update_list = UpdateList(model)
        self._update_list.props.model.connect('row-changed',
                                              self.__row_changed_cb)
        scrolled_window.add(self._update_list)
        self._update_list.show()

        bottom_box = gtk.HBox()
        bottom_box.set_spacing(style.DEFAULT_SPACING)
        self.pack_start(bottom_box, expand=False)
        bottom_box.show()

        self._size_label = gtk.Label()
        self._size_label.props.xalign = 0
        self._size_label.set_justify(gtk.JUSTIFY_LEFT)
        bottom_box.pack_start(self._size_label, expand=True)
        self._size_label.show()

        self.refresh_button = gtk.Button(stock=gtk.STOCK_REFRESH)
        bottom_box.pack_start(self.refresh_button, expand=False)
        self.refresh_button.show()

        self.install_button = gtk.Button(_('Install selected'))
        self.install_button.props.image = Icon(icon_name='emblem-downloads',
                                                icon_size=gtk.ICON_SIZE_BUTTON)
        bottom_box.pack_start(self.install_button, expand=False)
        self.install_button.show()

        self._update_total_size_label()

    def refresh(self):
        self._update_list.refresh()

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


class UpdateList(gtk.TreeView):

    def __init__(self, model):
        list_model = UpdateListModel(model)
        gtk.TreeView.__init__(self, list_model)

        self.set_reorderable(False)
        self.set_enable_search(False)
        self.set_headers_visible(False)

        toggle_renderer = gtk.CellRendererToggle()
        toggle_renderer.props.activatable = True
        toggle_renderer.props.xpad = style.DEFAULT_PADDING
        toggle_renderer.props.indicator_size = style.zoom(26)
        toggle_renderer.connect('toggled', self.__toggled_cb)

        toggle_column = gtk.TreeViewColumn()
        toggle_column.pack_start(toggle_renderer)
        toggle_column.add_attribute(toggle_renderer, 'active',
                                    UpdateListModel.SELECTED)
        self.append_column(toggle_column)

        icon_renderer = CellRendererIcon(self)
        icon_renderer.props.width = style.STANDARD_ICON_SIZE
        icon_renderer.props.height = style.STANDARD_ICON_SIZE
        icon_renderer.props.size = style.STANDARD_ICON_SIZE
        icon_renderer.props.xpad = style.DEFAULT_PADDING
        icon_renderer.props.ypad = style.DEFAULT_PADDING
        icon_renderer.props.stroke_color = style.COLOR_TOOLBAR_GREY.get_svg()
        icon_renderer.props.fill_color = style.COLOR_TRANSPARENT.get_svg()

        icon_column = gtk.TreeViewColumn()
        icon_column.pack_start(icon_renderer)
        icon_column.add_attribute(icon_renderer, 'file-name',
                                  UpdateListModel.ICON_FILE_NAME)
        self.append_column(icon_column)

        text_renderer = gtk.CellRendererText()

        description_column = gtk.TreeViewColumn()
        description_column.pack_start(text_renderer)
        description_column.add_attribute(text_renderer, 'markup',
                                         UpdateListModel.DESCRIPTION)
        self.append_column(description_column)

    def __toggled_cb(self, cell_renderer, path):
        row = self.props.model[path]
        row[UpdateListModel.SELECTED] = not row[UpdateListModel.SELECTED]

    def refresh(self):
        pass


class UpdateListModel(gtk.ListStore):

    BUNDLE_ID = 0
    SELECTED = 1
    ICON_FILE_NAME = 2
    DESCRIPTION = 3
    SIZE = 4

    def __init__(self, model):
        gtk.ListStore.__init__(self, str, bool, str, str, int)

        for bundle_update in model.updates:
            row = [None] * 5
            row[self.BUNDLE_ID] = bundle_update.bundle.get_bundle_id()
            row[self.SELECTED] = True
            row[self.ICON_FILE_NAME] = bundle_update.bundle.get_icon()

            details = _('From version %(current)s to %(new)s (Size: %(size)s)')
            details = details % \
                    {'current': bundle_update.bundle.get_activity_version(),
                     'new': bundle_update.version,
                     'size': _format_size(bundle_update.size)}

            row[self.DESCRIPTION] = '<b>%s</b>\n%s' % \
                    (bundle_update.bundle.get_name(), details)

            row[self.SIZE] = bundle_update.size

            self.append(row)


def _format_size(size):
    """Convert a given size in bytes to a nicer better readable unit"""
    if size == 0:
        # TRANS: download size is 0
        return _('None')
    elif size < 1024:
        # TRANS: download size of very small updates
        return _('1 KB')
    elif size < 1024 * 1024:
        # TRANS: download size of small updates, e.g. '250 KB'
        return locale.format_string(_('%.0f KB'), size / 1024.0)
    else:
        # TRANS: download size of updates, e.g. '2.3 MB'
        return locale.format_string(_('%.1f MB'), size / 1024.0 / 1024)
