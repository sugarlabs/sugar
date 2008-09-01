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
import sys
import time

import gobject
import gtk
import wnck

checks_queue = []
checks_failed = []
checks_succeeded = []

class Check(object):
    def __init__(self):
        self.name = None
        self.succeeded = False
        self.start_time = None
        self.max_time = None
        self.timeout = None

    def start(self):
        self.start_time = time.time()

    def get_failed(self):
        if self.max_time and self.start_time:
            if time.time() - self.start_time > self.max_time:
                return True
        return False

    failed = property(get_failed)

class ShellCheck(Check):
    def start(self):
        Check.start(self)

        self.name = 'Shell'
        self.max_time = 10

        screen = wnck.screen_get_default()
        screen.connect('window-opened', self._window_opened_cb)

    def _window_opened_cb(self, screen, window):
        if window.get_window_type() == wnck.WINDOW_DESKTOP:
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
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')

    checks_queue.append(ShellCheck())

    checks_queue[0].start()
    gobject.timeout_add(500, _timeout_cb)

    gtk.main()

    if len(checks_failed) > 0:
        sys.exit(1)
