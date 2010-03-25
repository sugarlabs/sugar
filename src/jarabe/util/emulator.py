# Copyright (C) 2006-2008, Red Hat, Inc.
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
import signal
import subprocess
import time
from optparse import OptionParser

import gtk
import gobject

from sugar import env


default_dimensions = (800, 600)
def _run_xephyr(display, dpi, dimensions, fullscreen):
    cmd = [ 'Xephyr' ]
    cmd.append(':%d' % display)
    cmd.append('-ac') 

    screen_size = (gtk.gdk.screen_width(), gtk.gdk.screen_height())

    if (not dimensions) and (fullscreen is None) and \
       (screen_size < default_dimensions) :
        # no forced settings, screen too small => fit screen
        fullscreen = True
    elif (not dimensions) :
        # screen is big enough or user has en/disabled fullscreen manually
        # => use default size (will get ignored for fullscreen)
        dimensions = '%dx%d' % default_dimensions

    if not dpi :
        dpi = gtk.settings_get_default().get_property('gtk-xft-dpi') / 1024

    if fullscreen :
        cmd.append('-fullscreen')

    if dimensions :
        cmd.append('-screen')
        cmd.append(dimensions)

    if dpi :
        cmd.append('-dpi')
        cmd.append('%d' % dpi)

    cmd.append('-noreset')

    pipe = subprocess.Popen(cmd)

    os.environ['DISPLAY'] = ":%d" % (display)
    os.environ['SUGAR_EMULATOR_PID'] = str(pipe.pid)
    return pipe


def _check_server(display):
    result = subprocess.call(['xdpyinfo', '-display', ':%d' % display],
                             stdout=open(os.devnull, "w"),
                             stderr=open(os.devnull, "w"))
    return result == 0


def _kill_pipe(pipe):
    """Terminate and wait for child process."""
    try:
        os.kill(pipe.pid, signal.SIGTERM)
    except OSError:
        pass

    pipe.wait()


def _start_xephyr(dpi, dimensions, fullscreen):
    for display in range(30, 40):
        if not _check_server(display):
            pipe = _run_xephyr(display, dpi, dimensions, fullscreen)

            for i_ in range(10):
                if _check_server(display):
                    return pipe

                time.sleep(0.1)

            _kill_pipe(pipe)


def _start_window_manager():
    cmd = ['metacity']

    cmd.extend(['--no-force-fullscreen'])

    gobject.spawn_async(cmd, flags=gobject.SPAWN_SEARCH_PATH)

def _setup_env():
    os.environ['SUGAR_EMULATOR'] = 'yes'
    os.environ['GABBLE_LOGFILE'] = os.path.join(
            env.get_profile_path(), 'logs', 'telepathy-gabble.log')
    os.environ['SALUT_LOGFILE'] = os.path.join(
            env.get_profile_path(), 'logs', 'telepathy-salut.log')
    os.environ['STREAM_ENGINE_LOGFILE'] = os.path.join(
            env.get_profile_path(), 'logs', 'telepathy-stream-engine.log')


def main():
    """Script-level operations"""

    parser = OptionParser()
    parser.add_option('-d', '--dpi', dest='dpi', type="int",
                      help='Emulator dpi')
    parser.add_option('-s', '--scaling', dest='scaling',
                      help='Sugar scaling in %')
    parser.add_option('-i', '--dimensions', dest='dimensions',
                      help='Emulator dimensions (ex. 1200x900)')
    parser.add_option('-f', '--fullscreen', dest='fullscreen',
                      action='store_true', default=None,
                      help='Run emulator in fullscreen mode')
    parser.add_option('-F', '--no-fullscreen', dest='fullscreen',
                      action='store_false',
                      help='Do not run emulator in fullscreen mode')
    (options, args) = parser.parse_args()

    _setup_env()

    server = _start_xephyr(options.dpi, options.dimensions, options.fullscreen)

    if options.scaling:
        os.environ['SUGAR_SCALING'] = options.scaling

    command = ['dbus-launch', '--exit-with-session']

    if not args:
        command.append('sugar')
    else:
        _start_window_manager()

        if args[0].endswith('.py'):
            command.append('python')

        command.append(args[0])

    subprocess.call(command)
    _kill_pipe(server)
