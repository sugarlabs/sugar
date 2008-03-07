# Copyright (C) 2007 Red Hat, Inc.
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

import os
import time

from sugar import env

_MAX_BACKUP_DIRS = 3

def setup():
    logs_dir = env.get_logs_path()
    if not os.path.isdir(logs_dir):
        os.makedirs(logs_dir)

    backup_logs = []
    backup_dirs = []
    for f in os.listdir(logs_dir):
        path = os.path.join(logs_dir, f)
        if os.path.isfile(path):
            backup_logs.append(f)
        elif os.path.isdir(path):
            backup_dirs.append(path)    

    if len(backup_dirs) > _MAX_BACKUP_DIRS:
        backup_dirs.sort()
        root = backup_dirs[0]
        for f in os.listdir(root):
            os.remove(os.path.join(root, f))
        os.rmdir(root)

    if len(backup_logs) > 0:
        name = str(int(time.time()))
        backup_dir = os.path.join(logs_dir, name)
        os.mkdir(backup_dir)
        for log in backup_logs:
            source_path = os.path.join(logs_dir, log)
            dest_path = os.path.join(backup_dir, log)
            os.rename(source_path, dest_path)

