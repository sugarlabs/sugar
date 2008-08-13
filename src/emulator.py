# Copyright (C) 2006, Red Hat, Inc.
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
import logging
import subprocess
import time
from optparse import OptionParser

log = logging.getLogger( 'sugar-emulator' )
log.setLevel( logging.DEBUG )

import pygtk
pygtk.require('2.0')
import gtk
import gobject

from sugar import env

def _run_xephyr(display, dpi):
    log.info('Starting Xephyr on display %s', display)

    cmd = [ 'Xephyr' ]
    cmd.append(':%d' % display)
    cmd.append('-ac') 

    if gtk.gdk.screen_width() < 1200 or gtk.gdk.screen_height() < 900:
        cmd.append('-fullscreen')
    else:
        cmd.append('-screen')
        cmd.append('%dx%d' % (1200, 900))

    if not dpi:
        dpi = gtk.settings_get_default().get_property('gtk-xft-dpi') / 1024
    if dpi > 0:
        cmd.append('-dpi')
        cmd.append('%d' % dpi)

    log.debug('Xephyr command: %s', " ".join( cmd ))
    result = gobject.spawn_async(cmd, flags=gobject.SPAWN_SEARCH_PATH)
    pid = result[0]

    os.environ['DISPLAY'] = ":%d" % (display)
    os.environ['SUGAR_EMULATOR_PID'] = str(pid)

def _check_xephyr(display):
    result = subprocess.call(['xdpyinfo', '-display', ':%d' % display],
                             stdout=open(os.devnull, "w"),
                             stderr=open(os.devnull, "w"))
    return result == 0

def _start_xephyr(dpi=None):
    for display in range(100, 110):
        if not _check_xephyr(display):
            _run_xephyr(display, dpi)

            tries = 10
            while tries > 0:
                if _check_xephyr(display):
                    return
                else:
                    tries -= 1
                    time.sleep(0.1)

def _start_matchbox():
    log.info('Starting the matchbox window manager')
    cmd = ['matchbox-window-manager']

    cmd.extend(['-use_titlebar', 'no'])
    cmd.extend(['-theme', 'sugar'])

    log.debug('Matchbox command: %s', " ".join( cmd))
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
    parser.add_option('-x', '--xo-style', dest='xo_style',
                      action='store_true', help='use the XO style')
    (options, args) = parser.parse_args()

    logging.basicConfig()

    _setup_env()

    if options.xo_style:
        _start_xephyr(dpi=201)
    else:
        _start_xephyr()

    if options.xo_style:
        os.environ['SUGAR_THEME'] = 'sugar-xo'
        os.environ['SUGAR_XO_STYLE'] = 'yes'
    else:
        os.environ['SUGAR_XO_STYLE'] = 'no'

    command = ['dbus-launch', 'dbus-launch', '--exit-with-session']

    if not args:
        command.append('sugar-shell')
    else:
        _start_matchbox()

        if args[0].endswith('.py'):
            command.append('python')

        command.append(args[0])
    
    log.info("Attempting to launch sugar to replace this process: %s"
             % " ".join(command))
    os.execlp( *command )
