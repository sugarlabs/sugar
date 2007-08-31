# Copyright (C) 2007, One Laptop Per Child
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

import gtk
import os
import gobject
from gettext import gettext as _

from sugar.graphics.palette import Palette
from sugar.graphics.tray import TrayButton
from sugar.graphics.icon import Icon
from sugar.graphics import style

from view.frame.frameinvoker import FrameWidgetInvoker

class ActivityButton(TrayButton, gobject.GObject):
    __gtype_name__ = 'SugarActivityButton'
    __gsignals__ = {
        'remove_activity': (gobject.SIGNAL_RUN_FIRST,
                            gobject.TYPE_NONE, ([]))
        }

    def __init__(self, activity_info):
        TrayButton.__init__(self)

        icon = Icon(file=activity_info.icon,
                    stroke_color=style.COLOR_WHITE.get_svg(),
                    fill_color=style.COLOR_TRANSPARENT.get_svg())
        self.set_icon_widget(icon)
        icon.show()

        self._activity_info = activity_info
        self.setup_rollover_options()

    def get_bundle_id(self):
        return self._activity_info.service_name

    def setup_rollover_options(self):
        palette = Palette(self._activity_info.name)
        self.set_palette(palette)
        palette.props.invoker = FrameWidgetInvoker(self)

        menu_item = gtk.MenuItem(_('Remove'))
        menu_item.connect('activate', self.item_remove_cb)
        palette.menu.append(menu_item)
        menu_item.show()

    def item_remove_cb(self, widget):
        self.emit('remove_activity')
