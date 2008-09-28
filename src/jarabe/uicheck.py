# Copyright (C) 2008, Red Hat, Inc.
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

import logging
import os
import sys
import subprocess
import time

import gobject
import gtk
import wnck

from sugar import wm

from jarabe.model.homemodel import get_sugar_window_type
from jarabe import config

checks_queue = []
checks_failed = []
checks_succeeded = []

def get_dbus_version():
    p = subprocess.Popen(['dbus-daemon', '--version'], stdout=subprocess.PIPE)

    output = p.communicate()[0]
    first_line = output.split('\n')[0]

    return first_line.split(' ')[-1]

class Check(object):
    def __init__(self):
        self.name = None
        self.succeeded = False
        self.start_time = None
        self.max_time = None
        self.timeout = None

    def start(self):
        logging.info('Start %s check.' % self.name)

        self.start_time = time.time()

    def get_failed(self):
        if self.max_time and self.start_time:
            if time.time() - self.start_time > self.max_time:
                return True
        return False

    failed = property(get_failed)

class ShellCheck(Check):
    def __init__(self):
        Check.__init__(self)

        self.name = 'Shell'
        self.max_time = 30

    def start(self):
        Check.start(self)

        screen = wnck.screen_get_default()
        screen.connect('window-opened', self._window_opened_cb)

    def _window_opened_cb(self, screen, window):
        if window.get_window_type() == wnck.WINDOW_DESKTOP:
            self.succeeded = True

class ActivityCheck(Check):
    def __init__(self, bundle_id):
        Check.__init__(self)

        self.name = bundle_id
        self.max_time = 30

    def start(self):
        Check.start(self)

        self.launch_activity()

        screen = wnck.screen_get_default()
        screen.connect('window-opened', self._window_opened_cb)

    def launch_activity(self):
        from sugar.activity import activityfactory

        activityfactory.create(self.name)

    def _window_opened_cb(self, screen, window):
        if wm.get_bundle_id(window) == self.name and \
           get_sugar_window_type(window) != 'launcher':
            self.succeeded = True

def _timeout_cb():
    check = checks_queue[0]
    if check.failed:
        logging.info('%s check failed.' % (check.name))
        checks_failed.append(checks_queue.pop(0))
    elif check.succeeded:
        logging.info('%s check succeeded.' % (check.name))
        checks_succeeded.append(checks_queue.pop(0))
    else:
        return True

    if len(checks_queue) > 0:
        checks_queue[0].start()
    else:
        gtk.main_quit()

    return True

def main():
    os.environ['GTK2_RC_FILES'] = os.path.join(config.data_path, 'sugar.gtkrc')

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')

    checks_queue.append(ShellCheck())

    if get_dbus_version() >= '1.2.1':
        # FIXME needs to get a list of the installed activities
        checks_queue.append(ActivityCheck('org.laptop.Log'))
        checks_queue.append(ActivityCheck('org.laptop.Chat'))
        checks_queue.append(ActivityCheck('org.laptop.WebActivity'))
        checks_queue.append(ActivityCheck('org.laptop.Pippy'))
        checks_queue.append(ActivityCheck('org.laptop.Terminal'))
        checks_queue.append(ActivityCheck('org.laptop.AbiWordActivity'))

    checks_queue[0].start()
    gobject.timeout_add(500, _timeout_cb)

    gtk.main()

    if len(checks_failed) > 0:
        sys.exit(1)
