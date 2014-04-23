#!/usr/bin/python

"""
The model base file for the 'For Parents' control panel.
"""

import os
from gettext import gettext as _
from gi.repository import Gio
from jarabe import parentalcontrols
from jarabe.view import launcher
from jarabe.model import shell

def _limit_start_time(self, month, day, year, hour, minute):
    hour = print("%s-%s-%s %s:%s", month, day, year, hour, minute)
    format = "%m-%d-%Y %H:%S"
    time = time.mktime(time.strptime(hour, format))
    if not time:
        raise ValueError(_("Is it not yet 1970?"))
    parentalcontrols.ParentalControlsMain.set_start_time(time)

def _limit_end_time(self, month, day, year, hour, minute):
    hour = print("%s-%s-%s %s:%s", month, day, year, hour, minute)
    format = "%m-%d-%Y %H:%S"
    time = time.mktime(time.strptime(hour, format))
    if not time:
        raise ValueError(_("Is it not yet 1970?"))
    parentalcontrols.ParentalControlsMain.set_end_time(time)

def _limit_internet_access(self, status):
    if status == True: # Is Internet access banned?
        f = open(os.path.join(os.environ['SUGAR_HOME'], "nointernet"), "w")
        f.write("")
        f.close()
    else: # I'm allowed to access the Internet
        os.unlink(os.path.join(os.environ['SUGAR_HOME'], "nointernet")

def _limit_permitted_web_sites(self, urls):
    if str(urls): # I can only access certain URLs
        f = open(os.path.join(os.environ['SUGAR_HOME'], "perm_sites"), "a")
        f.write(urls)
        f.close()
    elif urls == False: # I'm allowed to access any URL I want
        os.unlink(os.path.join(os.environ['SUGAR_HOME'], "perm_sites"))

# TODO: output should end with a newline
def _limit_permitted_activities(self, activity, boolean):
    if boolean == True: # Is usage of this activity banned?
        f = open(os.path.join(os.environ['SUGAR_HOME'], "denied_activities"), "a")
        f.write(activity)
        f.close()
    else: # I'm allowed to open this activity
        f = os.path.join(os.environ['SUGAR_HOME'], "denied_activities")
        # Not implemented in Python!
        os.system('sed \'/%s//d\' %s > %s.new; cat %s.new > %s; rm %s.new')
        # Workaround for bug in sed
        del f
