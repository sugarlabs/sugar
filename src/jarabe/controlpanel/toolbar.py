# Copyright (C) 2007, 2008 One Laptop Per Child
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

from gi.repository import Gtk
import gettext
from gi.repository import GObject


def _(msg):
    return gettext.dgettext('sugar', msg)

from sugar4.graphics.icon import Icon
from sugar4.graphics.toolbutton import ToolButton
from sugar4.graphics import iconentry
from sugar4.graphics import style


class MainToolbar(Gtk.Box):
    """ Main toolbar of the control panel
    """
    __gtype_name__ = 'MainToolbar'

    __gsignals__ = {
        'stop-clicked': (GObject.SignalFlags.RUN_FIRST,
                         None,
                         ([])),
        'search-changed': (GObject.SignalFlags.RUN_FIRST,
                           None,
                           ([str])),
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.add_css_class('toolbar')

        self._add_separator()

        tool_item = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.append(tool_item)
        tool_item.set_visible(True)
        self._search_entry = Gtk.SearchEntry()
        text = _('Search in %s') % _('Settings')
        self._search_entry.set_placeholder_text(text)
        self._search_entry.connect('search-changed', self.__search_entry_changed_cb)
        tool_item.append(self._search_entry)
        self._search_entry.set_visible(True)

        self._add_separator(True)

        self.stop = ToolButton(icon_name='dialog-cancel')
        self.stop.set_tooltip_text(_('Done'))
        self.stop.connect('clicked', self.__stop_clicked_cb)
        self.stop.set_visible(True)
        self.append(self.stop)

    def get_entry(self):
        return self._search_entry

    def _add_separator(self, expand=False):
        spacer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        if expand:
            spacer.set_hexpand(True)
        else:
            spacer.set_size_request(style.DEFAULT_SPACING, -1)
        self.append(spacer)
        spacer.set_visible(True)

    def __search_entry_changed_cb(self, search_entry):
        self.emit('search-changed', search_entry.props.text)

    def __stop_clicked_cb(self, button):
        self.emit('stop-clicked')


class SectionToolbar(Gtk.Box):
    """ Toolbar of the sections of the control panel
    """
    __gtype_name__ = 'SectionToolbar'

    __gsignals__ = {
        'cancel-clicked': (GObject.SignalFlags.RUN_FIRST,
                           None,
                           ([])),
        'accept-clicked': (GObject.SignalFlags.RUN_FIRST,
                           None,
                           ([])),
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.add_css_class('toolbar')

        self._add_separator()

        self._icon = Icon()
        self._add_widget(self._icon)

        self._add_separator()

        self._title = Gtk.Label()
        self._title.add_css_class('toolbar-title')
        self._add_widget(self._title)

        self._add_separator(True)

        self.cancel_button = ToolButton(icon_name='dialog-cancel')
        self.cancel_button.set_tooltip_text(_('Cancel'))
        self.cancel_button.connect('clicked', self.__cancel_button_clicked_cb)
        self.append(self.cancel_button)
        self.cancel_button.set_visible(True)

        self.accept_button = ToolButton(icon_name='dialog-ok')
        self.accept_button.set_tooltip_text(_('Ok'))
        self.accept_button.connect('clicked', self.__accept_button_clicked_cb)
        self.append(self.accept_button)
        self.accept_button.set_visible(True)

    def get_icon(self):
        return self._icon

    def get_title(self):
        return self._title

    def _add_separator(self, expand=False):
        spacer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        if expand:
            spacer.set_hexpand(True)
        else:
            spacer.set_size_request(style.DEFAULT_SPACING, -1)
        self.append(spacer)
        spacer.set_visible(True)

    def _add_widget(self, widget, expand=False):
        tool_item = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        if expand:
            tool_item.set_hexpand(True)

        tool_item.append(widget)
        widget.set_visible(True)

        self.append(tool_item)
        tool_item.set_visible(True)

    def __cancel_button_clicked_cb(self, widget, data=None):
        self.emit('cancel-clicked')

    def __accept_button_clicked_cb(self, widget, data=None):
        self.emit('accept-clicked')
