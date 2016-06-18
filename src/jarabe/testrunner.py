# Copyright (C) 2013, Daniel Narvaez
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
import sys
import subprocess

from gi.repository import GLib

from sugar3.logger import get_logs_dir


def _test_child_watch_cb(pid, condition, log_file):
    if os.WIFEXITED(condition):
        log_file.close()
        sys.exit(os.WEXITSTATUS(condition))


def check_environment():
    run_test = os.environ.get("SUGAR_RUN_TEST", None)
    if run_test is not None:
        log_path = os.environ.get("SUGAR_TEST_LOG", None)
        if log_path is None:
            log_path = os.path.join(get_logs_dir(), "test.log")
            log_file = open(log_path, "w")
        else:
            log_file = open(log_path, "a")

        test_process = subprocess.Popen(run_test,
                                        stdout=log_file,
                                        stderr=subprocess.STDOUT,
                                        shell=True)

        GLib.child_watch_add(test_process.pid, _test_child_watch_cb, log_file)
