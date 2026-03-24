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
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.HORIZONTAL)

        self._add_separator()

        tool_item = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.append(tool_item)
        tool_item.show()
        self._search_entry = iconentry.IconEntry()
        self._search_entry.set_icon_from_name(iconentry.ICON_ENTRY_PRIMARY,
                                              'entry-search')
        self._search_entry.add_clear_button()
        self._search_entry.set_width_chars(25)
        text = _('Search in %s') % _('Settings')
        self._search_entry.set_placeholder_text(text)
        self._search_entry.connect('changed', self.__search_entry_changed_cb)
        tool_item.append(self._search_entry)
        self._search_entry.show()

        self._add_separator(True)

        self.stop = ToolButton(icon_name='dialog-cancel')
        self.stop.set_tooltip(_('Done'))
        self.stop.connect('clicked', self.__stop_clicked_cb)
        self.stop.show()
        self.append(self.stop)
        self.stop.show()

    def get_entry(self):
        return self._search_entry

    def _add_separator(self, expand=False):
        separator = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        if expand:
            separator.set_hexpand(True)
        else:
            separator.set_size_request(style.DEFAULT_SPACING, -1)
        self.append(separator)
        separator.show()

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
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.HORIZONTAL)

        self._add_separator()

        self._icon = Icon()
        self._add_widget(self._icon)

        self._add_separator()

        self._title = Gtk.Label()
        self._add_widget(self._title)

        self._add_separator(True)

        self.cancel_button = ToolButton('dialog-cancel')
        self.cancel_button.set_tooltip(_('Cancel'))
        self.cancel_button.connect('clicked', self.__cancel_button_clicked_cb)
        self.append(self.cancel_button)
        self.cancel_button.show()

        self.accept_button = ToolButton('dialog-ok')
        self.accept_button.set_tooltip(_('Ok'))
        self.accept_button.connect('clicked', self.__accept_button_clicked_cb)
        self.append(self.accept_button)
        self.accept_button.show()

    def get_icon(self):
        return self._icon

    def get_title(self):
        return self._title

    def _add_separator(self, expand=False):
        separator = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        if expand:
            separator.set_hexpand(True)
        else:
            separator.set_size_request(style.DEFAULT_SPACING, -1)
        self.append(separator)
        separator.show()

    def _add_widget(self, widget, expand=False):
        tool_item = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        tool_item.set_hexpand(expand)

        tool_item.append(widget)
        widget.show()

        self.append(tool_item)
        tool_item.show()

    def __cancel_button_clicked_cb(self, widget, data=None):
        self.emit('cancel-clicked')

    def __accept_button_clicked_cb(self, widget, data=None):
        self.emit('accept-clicked')
