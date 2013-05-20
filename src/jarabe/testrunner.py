# Copyright (C) 2013, Daniel Narvaez
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
import sys
import subprocess

from gi.repository import GLib


def _test_child_watch_cb(pid, condition, user_data):
    if os.WIFEXITED(condition):
        sys.exit(os.WEXITSTATUS(condition))


def check_environment():
    run_test = os.environ.get("SUGAR_RUN_TEST", None)
    if run_test:
        test_process = subprocess.Popen(run_test, shell=True)
        GLib.child_watch_add(test_process.pid, _test_child_watch_cb, None)
