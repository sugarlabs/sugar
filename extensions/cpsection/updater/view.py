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

gtk.gdk.threads_init()

_e = gobject.markup_escape_text

_DEBUG_VIEW_ALL = True

class ActivityUpdater(SectionView):
    def __init__(self, modelwrapper, alerts):
        SectionView.__init__(self)
        self.set_spacing(style.DEFAULT_SPACING)
        self.set_border_width(style.DEFAULT_SPACING * 2)

        # top label #
        self._top_label = gtk.Label()
        self._top_label.set_line_wrap(True)
        self._top_label.set_justify(gtk.JUSTIFY_LEFT)
        self._top_label.set_property('xalign', 0)

        # bottom label #
        bottom_label = gtk.Label()
        bottom_label.set_line_wrap(True)
        bottom_label.set_justify(gtk.JUSTIFY_LEFT)
        bottom_label.set_property('xalign', 0)
        bottom_label.set_markup(
                _('Software updates correct errors, eliminate security' \
                  'vulnerabilities, and provide new features.'))

        # main canvas #
        self.pack_start(self._top_label, expand=False)
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
        self._top_label.set_markup('<big>%s</big>' % \
                _('Checking for updates...'))
        self.progress_pane.switch_to_check_progress()
        self.bundle_list.freeze_notify()
        Thread(target=self._do_refresh).start()

    def _do_refresh(self): #@inhibit_suspend
        self.bundle_list.refresh_list(self._refresh_progress_cb)
        gobject.idle_add(self._refresh_done_cb)

    def _refresh_progress_cb(self, n, extra=None):
        gobject.idle_add(self._progress, n, extra)

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
        self._top_label.set_markup('<big>%s</big>' % _e(header))
        self.bundle_pane.refresh_update_size()

    def install_clicked_cb(self, widget, event, data=None):
        """Invoked when the 'ok' button is clicked."""
        self._top_label.set_markup('<big>%s</big>' %
                                  _('Installing updates...'))
        self.progress_pane.switch_to_download_progress()
        self.bundle_list.freeze_notify()
        Thread(target=self._do_install).start()

    def _do_install(self): #@inhibit_suspend
        installed = self.bundle_list.install_updates(self._refresh_progress_cb)
        gobject.idle_add(self._install_done, installed)

    def _install_done(self, installed):
        self.bundle_list.thaw_notify()
        header = ngettext("%s update was installed",
                          "%s updates were installed", installed) \
                          % installed
        self._top_label.set_markup('<big>%s</big>' % _e(header))
        self.progress_pane.update(0)
        self.progress_pane.switch_to_complete_message()

    def _progress(self, n, extra=None, icon=None):
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
        self._updater_activity = update_activity
        self.set_spacing(style.DEFAULT_PADDING)

        # activity list #
        vpaned = gtk.VPaned()
        bundles = BundleListView(update_activity, self)
        vpaned.pack1(bundles, resize=True, shrink=False)
        self.pack_start(vpaned, expand=True)

        # Install/refresh buttons #
        button_box = gtk.HBox()
        button_box.set_spacing(style.DEFAULT_SPACING)
        hbox = gtk.HBox()
        hbox.pack_end(button_box, expand=False)
        self._size_label = gtk.Label()
        self._size_label.set_property('xalign', 0)
        self._size_label.set_justify(gtk.JUSTIFY_LEFT)
        hbox.pack_start(self._size_label, expand=True)
        self.pack_end(hbox, expand=False)
        check_button = gtk.Button(stock=gtk.STOCK_REFRESH)
        check_button.connect('clicked', update_activity.refresh_cb, self)
        button_box.pack_start(check_button, expand=False)

        self._install_button = _make_button(_("Install selected"),
                name='emblem-downloads')
        self._install_button.connect('clicked',
                update_activity.install_clicked_cb, self)
        button_box.pack_start(self._install_button, expand=False)

        def is_valid_cb(bundle_list, __):
            self._install_button.set_sensitive(bundle_list.is_valid())
        update_activity.bundle_list.connect('notify::is-valid', is_valid_cb)

    def refresh_update_size(self):
        """Update the 'download size' label."""
        bundle_list = self._updater_activity.bundle_list
        size = bundle_list.updates_size()
        self._size_label.set_markup(_('Download size: %s') %
                                   model._humanize_size(size))
        self._install_button.set_sensitive(bundle_list.updates_selected()!=0)

    def switch(self):
        """Make the bundle list visible and the progress pane invisible."""
        for widget, v in [(self, True),
                          (self._updater_activity.progress_pane, False)]:# ,
                          #(self.activity_updater.expander, False)]:
            widget.set_property('visible', v)

class BundleListView(gtk.ScrolledWindow):
    """List view at the top, showing activities, versions, and sizes."""
    def __init__(self, update_activity, bundle_pane):
        gtk.ScrolledWindow.__init__(self)
        self._update_activity = update_activity
        self._bundle_pane = bundle_pane

        # create TreeView using a filtered treestore
        self._treeview = gtk.TreeView(self._update_activity.bundle_list)

        # toggle cell renderers #
        crbool = gtk.CellRendererToggle()
        crbool.set_property('activatable', True)
        crbool.set_property('xpad', style.DEFAULT_PADDING)
        crbool.set_property('indicator_size', style.zoom(26))
        crbool.connect('toggled', self.__toggled_cb)

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
        column_install = gtk.TreeViewColumn('Install', crbool)
        column_install.add_attribute(crbool, 'active',
                model.UPDATE_SELECTED)
        column_install.set_cell_data_func(crbool, hide_func)
        column = gtk.TreeViewColumn('Name')
        column.pack_start(cricon, expand=False)
        column.pack_start(crtext, expand=True)
        column.add_attribute(cricon, 'pixbuf', model.ICON)
        column.set_resizable(True)
        column.set_cell_data_func(cricon, hide_func)
        def markup_func(cell_layout, renderer, m, it):
            s = '<b>%s</b>' % _e(m.get_value(it, model.NAME))
            if m.get_value(it, model.IS_HEADER):
                s = '<big>%s</big>' % s
            desc = m.get_value(it, model.DESCRIPTION)
            if desc is not None and desc != '':
                s += '\n<small>%s</small>' % _e(desc)
            renderer.set_property('markup', s)
            insens_func(cell_layout, renderer, m, it)
        column.set_cell_data_func(crtext, markup_func)

        # add tvcolumn to treeview
        self._treeview.append_column(column_install)
        self._treeview.append_column(column)

        self._treeview.set_reorderable(False)
        self._treeview.set_enable_search(False)
        self._treeview.set_headers_visible(False)
        self._treeview.set_rules_hint(True)
        self._treeview.connect('button-press-event',
                self.__button_press_event_cb)

        def is_valid_cb(activity_list, __):
            self._treeview.set_sensitive(
                    self._update_activity.bundle_list.is_valid())
        self._update_activity.bundle_list.connect('notify::is-valid',
                                                    is_valid_cb)
        is_valid_cb(self._update_activity.bundle_list, None)

        self.add_with_viewport(self._treeview)
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

    def __toggled_cb(self, crbool, path):
        row = self._treeview.props.model[path]
        row[model.UPDATE_SELECTED] = not row[model.UPDATE_SELECTED]
        self._bundle_pane.refresh_update_size()

    def __button_press_event_cb(self, widget, event):
        """
        Show a context menu if a right click was performed on an update entry
        """
        if not (event.type == gtk.gdk.BUTTON_PRESS and event.button == 3):
            return

        menu = gtk.Menu()

        item = gtk.MenuItem(_("_Uncheck All"))
        item.connect("activate", self.__check_activate_cb, False)
        if self._update_activity.bundle_list.updates_available() == 0:
            item.set_property("sensitive", False)
        menu.add(item)

        item = gtk.MenuItem(_("_Check All"))
        item.connect("activate", self.__check_activate_cb, True)
        if self._update_activity.bundle_list.updates_available() == 0:
            item.set_property("sensitive", False)
        menu.add(item)

        menu.popup(None, None, None, 0, event.time)
        menu.show_all()

    def __check_activate_cb(self, sender, state):
        for i in self._update_activity.bundle_list:
            i[model.UPDATE_SELECTED] = state
        self._bundle_pane.refresh_update_size()

class ProgressPane(gtk.VBox):
    """Container which replaces the `ActivityPane` during refresh or
    install."""

    def __init__(self, update_activity):
        self._update_activity = update_activity
        gtk.VBox.__init__(self)
        self.set_spacing(style.DEFAULT_PADDING)
        self.set_border_width(style.DEFAULT_SPACING * 2)

        self._progress = gtk.ProgressBar()
        self._label = gtk.Label()
        self._label.set_line_wrap(True)
        self._label.set_property('xalign', 0.5)
        self._label.modify_fg(gtk.STATE_NORMAL,
                             style.COLOR_BUTTON_GREY.get_gdk_color())
        self._icon = gtk.Image()
        self._icon.set_property('height-request', style.STANDARD_ICON_SIZE)
        # make an HBox to center the various buttons.
        hbox = gtk.HBox()
        self._cancel_button = gtk.Button(stock=gtk.STOCK_CANCEL)
        self._refresh_button = gtk.Button(stock=gtk.STOCK_REFRESH)
        self._try_again_button = _make_button(_('Try again'),
                                             stock=gtk.STOCK_REFRESH)
        for widget, cb in [(self._cancel_button, update_activity.cancel_cb),
                          (self._refresh_button, update_activity.refresh_cb),
                          (self._try_again_button, update_activity.refresh_cb)]:
            widget.connect('clicked', cb, update_activity)
            hbox.pack_start(widget, expand=True, fill=False)

        self.pack_start(self._icon)
        self.pack_start(self._progress)
        self.pack_start(self._label)
        self.pack_start(hbox)

    def update(self, n, extra=None, icon=None):
        """Update the status of the progress pane.  `n` should be a float
        in [0, 1], or else None.  You can optionally provide extra information
        in `extra` or an icon in `icon`."""

        if n is None:
            self._progress.pulse()
        else:
            self._progress.set_fraction(n)
        extra = _e(extra) if extra is not None else ''
        self._label.set_markup(extra)
        self._icon.set_property('visible', icon is not None)
        if icon is not None:
            self._icon.set_from_pixbuf(icon)

    def switch_to_check_progress(self):
        self._switch(show_cancel=True, show_bar=True)
        self._label.set_markup(_('Checking for updates...'))

    def switch_to_download_progress(self):
        self._switch(show_cancel=True, show_bar=True)
        self._label.set_markup(_('Starting download...'))

    def switch_to_complete_message(self):
        self._switch(show_cancel=False, show_bar=False)
        self._label.set_markup('')

    def cancelling(self):
        self._cancel_button.set_sensitive(False)
        self._label.set_markup(_('Cancelling...'))

    def _switch(self, show_cancel, show_bar, show_try_again=False):
        """Make the progress pane visible and the activity pane invisible."""
        self._update_activity.bundle_pane.set_property('visible', False)
        self.set_property('visible', True)
        for widget, v in [(self._progress, show_bar),
                          (self._cancel_button, show_cancel),
                          (self._refresh_button,
                                not show_cancel and not show_try_again),
                          (self._try_again_button, show_try_again),
                          #(self._update_activity.expander, False)
                          ]:
            widget.set_property('visible', v)
        self._cancel_button.set_sensitive(True)
        #self._update_activity.expander.set_expanded(False)

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
