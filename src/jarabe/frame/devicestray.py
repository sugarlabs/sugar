# Copyright (C) 2008 One Laptop Per Child
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

import os
import logging

from sugar3.graphics import tray

from jarabe import config


class DevicesTray(tray.HTray):

    def __init__(self):
        tray.HTray.__init__(self, align=tray.ALIGN_TO_END)

        for f in os.listdir(os.path.join(config.ext_path, 'deviceicon')):
            if f.endswith('.py') and not f.startswith('__'):
                module_name = f[:-3]
                try:
                    mod = __import__('deviceicon.' + module_name, globals(),
                                     locals(), [module_name])
                    mod.setup(self)
                except Exception:
                    logging.exception('Exception while loading extension:')

    def add_device(self, view):
        index = 0
        relative_index = getattr(view, 'FRAME_POSITION_RELATIVE', -1)
        for item in self.get_children():
            current_relative_index = getattr(item, 'FRAME_POSITION_RELATIVE',
                                             0)
            if current_relative_index >= relative_index:
                index += 1
            else:
                break
        self.add_item(view, index=index)
        view.show()

    def remove_device(self, view):
        self.remove_item(view)
