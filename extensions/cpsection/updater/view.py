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

import logging
import gtk
import gobject
from threading import Thread
from gettext import gettext as _
from gettext import ngettext

from sugar.graphics import style
from jarabe.controlpanel.sectionview import SectionView

import model
from model import _humanize_size

gtk.gdk.threads_init()

_logger = logging.getLogger('update-activity')

_e = gobject.markup_escape_text

_DEBUG_VIEW_ALL = True

class ActivityUpdater(SectionView):
    def __init__(self, modelwrapper, alerts):
        SectionView.__init__(self)
        self.set_spacing(style.DEFAULT_SPACING)
        self.set_border_width(style.DEFAULT_SPACING * 2)

        # top label #
        self.top_label = gtk.Label()
        self.top_label.set_line_wrap(True)
        self.top_label.set_justify(gtk.JUSTIFY_LEFT)
        self.top_label.set_property('xalign', 0)

        # bottom label #
        bottom_label = gtk.Label()
        bottom_label.set_line_wrap(True)
        bottom_label.set_justify(gtk.JUSTIFY_LEFT)
        bottom_label.set_property('xalign', 0)
        bottom_label.set_markup(
                _('Software updates correct errors, eliminate security' \
                  'vulnerabilities, and provide new features.'))

        # main canvas #
        self.pack_start(self.top_label, expand=False)
        self.pack_start(gtk.HSeparator(), expand=False)
        self.pack_start(bottom_label, expand=False)

        # bundle pane #
        self.bundle_list = model.UpdateList()
        self.bundle_pane = BundlePane(self)
        self.pack_start(self.bundle_pane, expand=True)

        # progress pane #
        self.progress_pane = ProgressPane(self)
        self.pack_start(self.progress_pane, expand=True, fill=False)

        self.show_all()

        self.refresh_cb(None, None)

    # refresh #
    def refresh_cb(self, widget, event):
        self.top_label.set_markup('<big>%s</big>' % \
                _('Checking for updates...'))
        self.progress_pane.switch_to_check_progress()
        self.bundle_list.freeze_notify()
        Thread(target=self._do_refresh).start()

    def _do_refresh(self): #@inhibit_suspend
        self.bundle_list.refresh_list(self._refresh_progress_cb)
        gobject.idle_add(self._refresh_done_cb)

    def _refresh_progress_cb(self, n, extra=None):
        gobject.idle_add(self._progress_cb, n, extra)

    # refresh done #
    def _refresh_done_cb(self):
        """Invoked in main thread when the refresh is complete."""
        self.bundle_list.thaw_notify()
        avail = self.bundle_list.updates_available()
        if avail == 0:
            header = _("Your software is up-to-date")
            self.progress_pane.switch_to_complete_message()
        else:
            header = ngettext("You can install %s update",
                              "You can install %s updates", avail) \
                              % avail
            self.bundle_pane.switch()
        self.top_label.set_markup('<big>%s</big>' % _e(header))
        self.bundle_pane.refresh_update_size()

    def install_clicked_cb(self, widget, event, data=None):
        """Invoked when the 'ok' button is clicked."""
        self.top_label.set_markup('<big>%s</big>' %
                                  _('Installing updates...'))
        self.progress_pane.switch_to_download_progress()
        self.bundle_list.freeze_notify()
        Thread(target=self._do_install).start()

    def _do_install(self): #@inhibit_suspend
        installed = self.bundle_list.install_updates(self._refresh_progress_cb)
        gobject.idle_add(self._install_done_cb, installed)

    def _install_done_cb(self, installed):
        self.bundle_list.thaw_notify()
        header = ngettext("%s update was installed",
                          "%s updates were installed", installed) \
                          % installed
        self.top_label.set_markup('<big>%s</big>' % _e(header))
        self.progress_pane.update(0)
        self.progress_pane.switch_to_complete_message()

    def _progress_cb(self, n, extra=None, icon=None):
        """Invoked in main thread during a refresh operation."""
        self.progress_pane.update(n, extra, icon)

    def cancel_cb(self, widget, event, data=None):
        """Callback when the cancel button is clicked."""
        self.bundle_list.cancel()
        self.progress_pane.cancelling()

class BundlePane(gtk.VBox):
    """Container for the activity and group lists."""

    def __init__(self, update_activity):
        gtk.VBox.__init__(self)
        self.updater_activity = update_activity
        self.set_spacing(style.DEFAULT_PADDING)

        # activity list #
        vpaned = gtk.VPaned()
        self.bundles = BundleListView(update_activity, self)
        vpaned.pack1(self.bundles, resize=True, shrink=False)
        self.pack_start(vpaned, expand=True)

        # Install/refresh buttons #
        button_box = gtk.HBox()
        button_box.set_spacing(style.DEFAULT_SPACING)
        hbox = gtk.HBox()
        hbox.pack_end(button_box, expand=False)
        self.size_label = gtk.Label()
        self.size_label.set_property('xalign', 0)
        self.size_label.set_justify(gtk.JUSTIFY_LEFT)
        hbox.pack_start(self.size_label, expand=True)
        self.pack_end(hbox, expand=False)
        self.check_button = gtk.Button(stock=gtk.STOCK_REFRESH)
        self.check_button.connect('clicked', update_activity.refresh_cb, self)
        button_box.pack_start(self.check_button, expand=False)

        self.install_button = _make_button(_("Install selected"),
                name='emblem-downloads')
        self.install_button.connect('clicked',
                update_activity.install_clicked_cb, self)
        button_box.pack_start(self.install_button, expand=False)

        def is_valid_cb(bundle_list, __):
            self.install_button.set_sensitive(bundle_list.is_valid())
        update_activity.bundle_list.connect('notify::is-valid', is_valid_cb)

    def refresh_update_size(self):
        """Update the 'download size' label."""
        bundle_list = self.updater_activity.bundle_list
        size = bundle_list.updates_size()
        self.size_label.set_markup(_('Download size: %s') %
                                   _humanize_size(size))
        self.install_button.set_sensitive(bundle_list.updates_selected()!=0)

    def switch(self):
        """Make the bundle list visible and the progress pane invisible."""
        for widget, v in [(self, True),
                          (self.updater_activity.progress_pane, False)]:# ,
                          #(self.activity_updater.expander, False)]:
            widget.set_property('visible', v)

class BundleListView(gtk.ScrolledWindow):
    """List view at the top, showing activities, versions, and sizes."""
    def __init__(self, update_activity, bundle_pane):
        gtk.ScrolledWindow.__init__(self)
        self.update_activity = update_activity
        self.bundle_pane = bundle_pane

        # create TreeView using a filtered treestore
        self.treeview = gtk.TreeView(self.update_activity.bundle_list)

        # toggle cell renderers #
        crbool = gtk.CellRendererToggle()
        crbool.set_property('activatable', True)
        crbool.set_property('xpad', style.DEFAULT_PADDING)
        crbool.set_property('indicator_size', style.zoom(26))
        crbool.connect('toggled', self.toggled_cb)

        # icon cell renderers #
        cricon = gtk.CellRendererPixbuf()
        cricon.set_property('width', style.STANDARD_ICON_SIZE)
        cricon.set_property('height', style.STANDARD_ICON_SIZE)

        # text cell renderers #
        crtext = gtk.CellRendererText()
        crtext.set_property('xpad', style.DEFAULT_PADDING)
        crtext.set_property('ypad', style.DEFAULT_PADDING)

        #create the TreeViewColumn to display the data
        def view_func_maker(propname):
            def view_func(cell_layout, renderer, m, it):
                renderer.set_property(propname,
                                      not m.get_value(it, model.IS_HEADER))
            return view_func
        hide_func = view_func_maker('visible')
        insens_func = view_func_maker('sensitive')
        self.column_install = gtk.TreeViewColumn('Install', crbool)
        self.column_install.add_attribute(crbool, 'active',
                model.UPDATE_SELECTED)
        self.column_install.set_cell_data_func(crbool, hide_func)
        self.column = gtk.TreeViewColumn('Name')
        self.column.pack_start(cricon, expand=False)
        self.column.pack_start(crtext, expand=True)
        self.column.add_attribute(cricon, 'pixbuf', model.ICON)
        self.column.set_resizable(True)
        self.column.set_cell_data_func(cricon, hide_func)
        def markup_func(cell_layout, renderer, m, it):
            s = '<b>%s</b>' % _e(m.get_value(it, model.NAME))
            if m.get_value(it, model.IS_HEADER):
                s = '<big>%s</big>' % s
            desc = m.get_value(it, model.DESCRIPTION)
            if desc is not None and desc != '':
                s += '\n<small>%s</small>' % _e(desc)
            renderer.set_property('markup', s)
            insens_func(cell_layout, renderer, m, it)
        self.column.set_cell_data_func(crtext, markup_func)

        # add tvcolumn to treeview
        self.treeview.append_column(self.column_install)
        self.treeview.append_column(self.column)

        self.treeview.set_reorderable(False)
        self.treeview.set_enable_search(False)
        self.treeview.set_headers_visible(False)
        self.treeview.set_rules_hint(True)
        self.treeview.connect('button-press-event', self.show_context_menu)

        def is_valid_cb(activity_list, __):
            self.treeview.set_sensitive(
                    self.update_activity.bundle_list.is_valid())
        self.update_activity.bundle_list.connect('notify::is-valid',
                                                    is_valid_cb)
        is_valid_cb(self.update_activity.bundle_list, None)

        self.add_with_viewport(self.treeview)
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

    def toggled_cb(self, crbool, path):
        row = self.treeview.props.model[path]
        row[model.UPDATE_SELECTED] = not row[model.UPDATE_SELECTED]
        self.bundle_pane.refresh_update_size()

    def show_context_menu(self, widget, event):
        """
        Show a context menu if a right click was performed on an update entry
        """
        if not (event.type == gtk.gdk.BUTTON_PRESS and event.button == 3):
            return

        menu = gtk.Menu()

        item = gtk.MenuItem(_("_Uncheck All"))
        item.connect("activate", self.__check_activate_cb, False)
        if self.update_activity.bundle_list.updates_available() == 0:
            item.set_property("sensitive", False)
        menu.add(item)

        item = gtk.MenuItem(_("_Check All"))
        item.connect("activate", self.__check_activate_cb, True)
        if self.update_activity.bundle_list.updates_available() == 0:
            item.set_property("sensitive", False)
        menu.add(item)

        menu.popup(None, None, None, 0, event.time)
        menu.show_all()

    def __check_activate_cb(self, sender, state):
        for i in self.update_activity.bundle_list:
            i[model.UPDATE_SELECTED] = state
        self.bundle_pane.refresh_update_size()

class ProgressPane(gtk.VBox):
    """Container which replaces the `ActivityPane` during refresh or
    install."""

    def __init__(self, update_activity):
        self.update_activity = update_activity
        gtk.VBox.__init__(self)
        self.set_spacing(style.DEFAULT_PADDING)
        self.set_border_width(style.DEFAULT_SPACING * 2)

        self.progress = gtk.ProgressBar()
        self.label = gtk.Label()
        self.label.set_line_wrap(True)
        self.label.set_property('xalign', 0.5)
        self.label.modify_fg(gtk.STATE_NORMAL,
                             style.COLOR_BUTTON_GREY.get_gdk_color())
        self.icon = gtk.Image()
        self.icon.set_property('height-request', style.STANDARD_ICON_SIZE)
        # make an HBox to center the various buttons.
        hbox = gtk.HBox()
        self.cancel_button = gtk.Button(stock=gtk.STOCK_CANCEL)
        self.refresh_button = gtk.Button(stock=gtk.STOCK_REFRESH)
        self.try_again_button = _make_button(_('Try again'),
                                             stock=gtk.STOCK_REFRESH)
        for widget, cb in [(self.cancel_button, update_activity.cancel_cb),
                          (self.refresh_button, update_activity.refresh_cb),
                          (self.try_again_button, update_activity.refresh_cb)]:
            widget.connect('clicked', cb, update_activity)
            hbox.pack_start(widget, expand=True, fill=False)

        self.pack_start(self.icon)
        self.pack_start(self.progress)
        self.pack_start(self.label)
        self.pack_start(hbox)

    def update(self, n, extra=None, icon=None):
        """Update the status of the progress pane.  `n` should be a float
        in [0, 1], or else None.  You can optionally provide extra information
        in `extra` or an icon in `icon`."""

        if n is None:
            self.progress.pulse()
        else:
            self.progress.set_fraction(n)
        extra = _e(extra) if extra is not None else ''
        self.label.set_markup(extra)
        self.icon.set_property('visible', icon is not None)
        if icon is not None:
            self.icon.set_from_pixbuf(icon)

    def switch_to_check_progress(self):
        self._switch(show_cancel=True, show_bar=True)
        self.label.set_markup(_('Checking for updates...'))

    def switch_to_download_progress(self):
        self._switch(show_cancel=True, show_bar=True)
        self.label.set_markup(_('Starting download...'))

    def switch_to_complete_message(self):
        self._switch(show_cancel=False, show_bar=False)
        self.label.set_markup('')

    def cancelling(self):
        self.cancel_button.set_sensitive(False)
        self.label.set_markup(_('Cancelling...'))

    def _switch(self, show_cancel, show_bar, show_try_again=False):
        """Make the progress pane visible and the activity pane invisible."""
        self.update_activity.bundle_pane.set_property('visible', False)
        self.set_property('visible', True)
        for widget, v in [(self.progress, show_bar),
                          (self.cancel_button, show_cancel),
                          (self.refresh_button,
                                not show_cancel and not show_try_again),
                          (self.try_again_button, show_try_again),
                          #(self.update_activity.expander, False)
                          ]:
            widget.set_property('visible', v)
        self.cancel_button.set_sensitive(True)
        #self.update_activity.expander.set_expanded(False)

def _make_button(label_text, stock=None, name=None):
    """Convenience function to make labelled buttons with images."""
    b = gtk.Button()
    hbox = gtk.HBox()
    hbox.set_spacing(style.DEFAULT_PADDING)
    i = gtk.Image()
    if stock is not None:
        i.set_from_stock(stock, gtk.ICON_SIZE_BUTTON)
    if name is not None:
        i.set_from_icon_name(name, gtk.ICON_SIZE_BUTTON)
    hbox.pack_start(i, expand=False)
    l = gtk.Label(label_text)
    hbox.pack_start(l, expand=False)
    b.add(hbox)
    return b
