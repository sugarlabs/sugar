"""Logging module configuration for Sugar"""
# Copyright (C) 2006-2007 Red Hat, Inc.
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

import sys
import os
import logging
import time

_MAX_BACKUP_DIRS = 3

def setup_logs_dir():
    logs_dir = get_logs_dir()
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

def get_logs_dir():
    profile = os.environ.get('SUGAR_PROFILE', 'default')
    logs_dir = os.path.join(os.path.expanduser('~'),
                            '.sugar', profile, 'logs')
    return logs_dir

def set_level(level):
    levels = { 'error'   : logging.ERROR,
               'warning' : logging.WARNING,
               'debug'   : logging.DEBUG,
               'info'    : logging.INFO }
    if levels.has_key(level):
        logging.getLogger('').setLevel(levels[level])

def start(log_filename=None, redirect_io=True):
    if os.environ.has_key('SUGAR_LOGGER_LEVEL'):
        set_level(os.environ['SUGAR_LOGGER_LEVEL'])

    if log_filename:
        log_path = os.path.join(get_logs_dir(), log_filename + '.log')
        log_file = open(log_path, 'w')

        handler = logging.StreamHandler(log_file)
        logging.getLogger('').addHandler(handler)

        if redirect_io:
            os.dup2(log_file.fileno(), sys.stdout.fileno())
            os.dup2(log_file.fileno(), sys.stderr.fileno())
