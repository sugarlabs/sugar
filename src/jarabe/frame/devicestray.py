# Copyright (C) 2008 One Laptop Per Child
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

import os

from sugar.graphics import tray

from jarabe import config

class DevicesTray(tray.HTray):
    def __init__(self):
        tray.HTray.__init__(self, align=tray.ALIGN_TO_END)

        for f in os.listdir(os.path.join(config.ext_path, 'deviceicon')):
            if f.endswith('.py') and not f.startswith('__'):
                module_name = f[:-3]
                mod = __import__('deviceicon.' + module_name, globals(),
                                 locals(), [module_name])
                mod.setup(self)

    def add_device(self, view):
        index = 0
        for item in self.get_children():
            index = self.get_item_index(item)
            view_pos = getattr(view, "FRAME_POSITION_RELATIVE", -1)
            item_pos = getattr(item, "FRAME_POSITION_RELATIVE", 0)
            if view_pos < item_pos:
                break
        self.add_item(view, index=index)
        view.show()

    def remove_device(self, view):
        self.remove_item(view)
