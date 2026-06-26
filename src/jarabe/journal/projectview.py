# Copyright (C) 2016, Abhijit Patel
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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

from gettext import gettext as _

from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import Pango
from gi.repository import Gdk
from gi.repository import Gio

from jarabe.journal.expandedentry import TextView
from jarabe.journal.expandedentry import BaseExpandedEntry
from jarabe.journal.detailview import BackBar
from jarabe.journal.listview import ListView
from jarabe.journal import model

from sugar4.graphics.xocolor import XoColor
from sugar4.graphics import style
from sugar4.graphics.icon import Icon

_SERVICE_NAME = 'org.laptop.Activity'
_SERVICE_PATH = '/org/laptop/Activity'
_SERVICE_INTERFACE = 'org.laptop.Activity'


class ProjectView(Gtk.Box, BaseExpandedEntry):

    __gsignals__ = {
        'go-back-clicked': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)
        BaseExpandedEntry.__init__(self)
        self.project_metadata = None
        self._service = None
        self._activity_id = None
        self._project = None
        
        self.add_css_class('project-view-bg')

        self._vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.append(self._vbox)

        back_bar = BackBar()
        click = Gtk.GestureClick()
        click.connect('released', self.__back_bar_release_event_cb)
        back_bar.add_controller(click)
        self._vbox.append(back_bar)

        header = self.create_header()
        header.set_margin_bottom(style.DEFAULT_SPACING * 2)
        self._vbox.append(header)
        header.set_visible(True)

        description_box, self._description = self._create_description()
        description_box.set_vexpand(True)
        description_box.set_margin_bottom(int(style.DEFAULT_SPACING / 3))
        self._vbox.append(description_box)

        # Gtk.Entry doesn't have focus-out-event, we use Gtk.EventControllerFocus
        focus_controller = Gtk.EventControllerFocus()
        focus_controller.connect('leave', self._title_focus_out_event_cb)
        self._title.add_controller(focus_controller)

        settings = Gio.Settings.new('org.sugarlabs.user')
        icon_color = settings.get_string('color')

        self._icon = Icon(icon_name='project-box',
                          pixel_size=style.MEDIUM_ICON_SIZE)
        self._icon.xo_color = XoColor(icon_color)
        self._icon_box.append(self._icon)

    def get_vbox(self):
        return self._vbox

    def create_list_view_project(self):
        self._list_view_project = ListView(self)
        return self._list_view_project

    def get_list_view(self):
        return self._list_view_project

    def get_mount_point(self):
        return '/'

    def __back_bar_release_event_cb(self, gesture, n_press, x, y):
        self.emit('go-back-clicked')
        return False

    def set_project_metadata(self, project_metadata):
        self.project_metadata = project_metadata

        description = project_metadata.get('description', '')
        self._description.get_buffer().set_text(description, len(description))
        self._title.set_text(project_metadata.get('title', ''))

    def _title_focus_out_event_cb(self, controller):
        self._update_entry()

    def _create_description(self):
        widget = TextView()
        focus_controller = Gtk.EventControllerFocus()
        focus_controller.connect('leave', self._description_tags_focus_out_event_cb)
        widget.add_controller(focus_controller)
        return self._create_scrollable(widget, label=_('Description:')), widget

    def _description_tags_focus_out_event_cb(self, controller):
        self._update_entry()

    def _update_entry(self):
        # updating description
        bounds = self._description.get_buffer().get_bounds()
        old_description = self.project_metadata.get('description', None)
        new_description = self._description.get_buffer().get_text(
            bounds[0], bounds[1], False)

        if old_description != new_description:
            self.project_metadata['description'] = new_description
            model.write(self.project_metadata)

        new_title = self._title.get_text()
        old_title = self.project_metadata.get('title', '')

        if old_title != new_title:
            self.project_metadata['title'] = new_title
            model.write(self.project_metadata)

    def _create_scrollable(self, widget, label=None):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_spacing(style.DEFAULT_SPACING)

        if label is not None:
            text = Gtk.Label()
            text.set_markup('<span foreground="%s">%s</span>' % (
                style.COLOR_BUTTON_GREY.get_html(), label))

            halign = Gtk.Box()
            halign.set_halign(Gtk.Align.START)
            halign.append(text)
            vbox.append(halign)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC,
                                   Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_has_frame(True)
        scrolled_window.set_child(widget)
        scrolled_window.set_vexpand(True)
        vbox.append(scrolled_window)

        return vbox
