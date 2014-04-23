#!/usr/bin/python

# The core file for Sugar parental controls.

"""
The core file for Sugar parental controls.
"""

import logging
import os
import shutil
import urlparse
import tempfile
import time

from subprocess import call
from gettext import gettext as _
from gi.repository import GObject, Gtk, Gdk
from sugar3 import mime
from sugar3.graphics.alert import Alert
from sugar3.graphics.icon import Icon
from jarabe.view.buddymenu import _quit

class ParentalControlsMain(self):
    def __init__(self):
        endtime = self.get_end_time()
        now = time.ctime()

        # Don't show the alert until it's time to do so!
        while now != endtime:
            pass

        # Show the alert when it becomes time to do so
        self._show_expired_time_dialog()

    def _turn_me_on(self):
        call(['/usr/bin/sugar-su', 'bash', '-c', '\'echo 1 > $SUGAR_HOME/controls_on\''])

    def _turn_me_off(self):
        call(['/usr/bin/sugar-su', 'bash', '-c', '\'echo 0 > $SUGAR_HOME/controls_on\''])

    def _show_expired_time_dialog(self):
        alert = Alert()
        alert.props.title = _('Your computer time is over.')
        alert.props.msg = _('Please save all work and shut down or log out.')

        cancel_icon = Icon(icon_name='dialog-cancel')
        alert.add_button(self.grant_extended_time, _('Give me more time!'),
                         cancel_icon)

        logout_icon = Icon(icon_name='system-logout')
        alert.add_button(self.log_me_off, _('Logout'), logout_icon)

        self.add_alert(alert)
        alert.connect('response', self._alert_response_cb)

        self.reveal()

    def grant_extended_time(self):
        call(['sugar-su', 'sugar-ext-time'])

    def log_me_off(self):
        _quit(get_session_manager().logout)

    def get_start_time(self):    
        f = open(os.path.join(os.environ['SUGAR_HOME'], 'starttime'))
        print f.read()
        f.close()

    def set_start_time(self, starttime):
        f = open(os.path.join(os.environ['SUGAR_HOME'], 'starttime'), 'w')
        f.write(starttime)
        f.close()

    def get_end_time(self):
        f = open(os.path.join(os.environ['SUGAR_HOME'], 'endtime'))
        print f.read()
        f.close()

    def set_end_time(self, endtime):
        f = open(os.path.join(os.environ['SUGAR_HOME'], 'endtime'))
        f.write(endtime)
        f.close()
