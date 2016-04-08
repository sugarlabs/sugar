#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2016  Utkarsh Tiwari
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
#
# Contact information:
# Utkarsh Tiwari    iamutkarshtiwari@gmail.com

from gi.repository import Gtk
import gettext
from gi.repository import GObject

_ = lambda msg: gettext.dgettext('sugar', msg)

from sugar3.graphics.icon import Icon
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics import iconentry
from sugar3.graphics import style


class MainToolbar(Gtk.Toolbar):
    """ Main toolbar of the screenshot panel
    """
    __gtype_name__ = 'ScreenshotMainToolbar'

    __gsignals__ = {
        'stop-clicked': (GObject.SignalFlags.RUN_FIRST,
                         None,
                         ([])),
        'ok-clicked': (GObject.SignalFlags.RUN_FIRST,
                         None,
                         ([])),
    }

    def __init__(self):
        Gtk.Toolbar.__init__(self)

        self._add_separator()

        tool_item = Gtk.ToolItem()
        self.insert(tool_item, -1)
        tool_item.show()

        message = Gtk.Label()
        message.set_markup("<b>"+gettext.gettext('Save Screenshot')+"</b>")
        tool_item.add(message)
        message.show()

        self._add_separator(True)

        self.stop = ToolButton(icon_name='dialog-cancel')
        self.stop.set_tooltip(_('Cancel'))
        self.stop.connect('clicked', self.__stop_clicked_cb)
        self.insert(self.stop, -1)
        self.stop.show()

        self.accept = ToolButton(icon_name='dialog-ok')
        self.accept.set_tooltip(_('Save'))
        self.accept.connect('clicked', self.__ok_clicked_cb)
        self.insert(self.accept, -1)
        self.accept.show()

    def _add_separator(self, expand=False):
        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        if expand:
            separator.set_expand(True)
        else:
            separator.set_size_request(style.DEFAULT_SPACING, -1)
        self.insert(separator, -1)
        separator.show()

    def __stop_clicked_cb(self, button):
        self.emit('stop-clicked')

    def __ok_clicked_cb(self, button):
        self.emit('ok-clicked')