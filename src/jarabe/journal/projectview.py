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

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gio

from jarabe.journal.expandedentry import TextView
from jarabe.journal.expandedentry import BaseExpandedEntry
from jarabe.journal.detailview import BackBar
from jarabe.journal.listview import ListView
from jarabe.journal import model

from sugar3.graphics.xocolor import XoColor
from sugar3.graphics import style
from sugar3.graphics.icon import Icon

_SERVICE_NAME = 'org.laptop.Activity'
_SERVICE_PATH = '/org/laptop/Activity'
_SERVICE_INTERFACE = 'org.laptop.Activity'


class ProjectView(Gtk.EventBox, BaseExpandedEntry):

    __gsignals__ = {
        'go-back-clicked': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, **kwargs):
        Gtk.EventBox.__init__(self)
        BaseExpandedEntry.__init__(self)
        self.project_metadata = None
        self._service = None
        self._activity_id = None
        self._project = None
        self.modify_bg(Gtk.StateType.NORMAL, style.COLOR_WHITE.get_gdk_color())

        self._vbox = Gtk.VBox()
        self.add(self._vbox)

        back_bar = BackBar()
        back_bar.connect('button-release-event',
                         self.__back_bar_release_event_cb)
        self._vbox.pack_start(back_bar, False, True, 0)

        header = self.create_header()
        self._vbox.pack_start(header, False, False, style.DEFAULT_SPACING * 2)
        header.show()

        description_box, self._description = self._create_description()
        self._vbox.pack_start(description_box, False, True,
                              style.DEFAULT_SPACING/3)

        self._title.connect('focus-out-event', self._title_focus_out_event_cb)

        settings = Gio.Settings('org.sugarlabs.user')
        icon_color = settings.get_string('color')

        self._icon = Icon(icon_name='project-box',
                          pixel_size=style.MEDIUM_ICON_SIZE)
        self._icon.xo_color = XoColor(icon_color)
        self._icon_box.pack_start(self._icon, False, False, 0)

    def get_vbox(self):
        return self._vbox

    def create_list_view_project(self):
        self._list_view_project = ListView(self)
        return self._list_view_project

    def get_list_view(self):
        return self._list_view_project

    def get_mount_point(self):
        return '/'

    def __back_bar_release_event_cb(self, back_bar, event):
        self.emit('go-back-clicked')
        return False

    def set_project_metadata(self, project_metadata):
        self.project_metadata = project_metadata

        description = project_metadata.get('description', '')
        self._description.get_buffer().set_text(description)
        self._title.set_text(project_metadata.get('title', ''))

    def _title_focus_out_event_cb(self, entry, event):
        self._update_entry()

    def _create_description(self):
        widget = TextView()
        widget.connect('focus-out-event',
                       self._description_tags_focus_out_event_cb)
        return self._create_scrollable(widget, label=_('Description:')), widget

    def _description_tags_focus_out_event_cb(self, text_view, event):
        self._update_entry()

    def _update_entry(self):
        #updating description
        bounds = self._description.get_buffer().get_bounds()
        old_description = self.project_metadata.get('description', None)
        new_description = self._description.get_buffer().get_text(
            bounds[0], bounds[1], include_hidden_chars=False)

        if old_description != new_description:
            self.project_metadata['description'] = new_description
            model.write(self.project_metadata)

        new_title = self._title.get_text()
        old_title = self.project_metadata.get('title', '')

        if old_title != new_title:
            self.project_metadata['title'] = new_title
            model.write(self.project_metadata)

    def _create_scrollable(self, widget, label=None):
        vbox = Gtk.VBox()
        vbox.props.spacing = style.DEFAULT_SPACING

        if label is not None:
            text = Gtk.Label()
            text.set_markup('<span foreground="%s">%s</span>' % (
                style.COLOR_BUTTON_GREY.get_html(), label))

            halign = Gtk.Alignment.new(0, 0, 0, 0)
            halign.add(text)
            vbox.pack_start(halign, False, False, 0)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC,
                                   Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        scrolled_window.add(widget)
        vbox.pack_start(scrolled_window, True, True, 0)

        return vbox
