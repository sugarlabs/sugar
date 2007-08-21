import sys 
import os
import thread
import socket
import signal
import traceback

import commands

import gobject

__sys_path = list(sys.path)
import gtk
sys.path = __sys_path

import irc
from conf import conf

import widgets
import windows

# Running from same package dir
urkpath = os.path.dirname(__file__)

def path(filename=""):
    if filename:
        return os.path.join(urkpath, filename)
    else:
        return urkpath

# Priority Constants
PRIORITY_HIGH = gobject.PRIORITY_HIGH
PRIORITY_DEFAULT = gobject.PRIORITY_DEFAULT
PRIORITY_HIGH_IDLE = gobject.PRIORITY_HIGH_IDLE
PRIORITY_DEFAULT_IDLE = gobject.PRIORITY_DEFAULT_IDLE
PRIORITY_LOW = gobject.PRIORITY_LOW


if os.access(path('profile'),os.F_OK) or os.path.expanduser("~") == "~":
    userpath = path('profile')
    if not os.access(userpath,os.F_OK):
        os.mkdir(userpath)
    if not os.access(os.path.join(userpath,'scripts'),os.F_OK):
        os.mkdir(os.path.join(userpath,'scripts'))
else:
    userpath = os.path.join(os.path.expanduser("~"), ".urk")
    if not os.access(userpath,os.F_OK):
        os.mkdir(userpath, 0700)
    if not os.access(os.path.join(userpath,'scripts'),os.F_OK):
        os.mkdir(os.path.join(userpath,'scripts'), 0700)


def set_clipboard(text):
    gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD).set_text(text)
    gtk.clipboard_get(gtk.gdk.SELECTION_PRIMARY).set_text(text)

class Source(object):
    __slots__ = ['enabled']
    def __init__(self):
        self.enabled = True
    def unregister(self):
        self.enabled = False

class GtkSource(object):
    __slots__ = ['tag']
    def __init__(self, tag):
        self.tag = tag
    def unregister(self):
        gobject.source_remove(self.tag)

def register_idle(f, *args, **kwargs):
    priority = kwargs.pop("priority",PRIORITY_DEFAULT_IDLE)
    def callback():
        return f(*args, **kwargs)
    return GtkSource(gobject.idle_add(callback, priority=priority))

def register_timer(time, f, *args, **kwargs):
    priority = kwargs.pop("priority",PRIORITY_DEFAULT_IDLE)
    def callback():
        return f(*args, **kwargs)
    return GtkSource(gobject.timeout_add(time, callback, priority=priority))

def fork(cb, f, *args, **kwargs):
    is_stopped = Source()
    def thread_func():
        try:
            result, error = f(*args, **kwargs), None
        except Exception, e:
            result, error = None, e

        if is_stopped.enabled:
            def callback():           
                if is_stopped.enabled:
                    cb(result, error)

            gobject.idle_add(callback)

    thread.start_new_thread(thread_func, ())
    return is_stopped

set_style = widgets.set_style

def we_get_signal(*what):
    gobject.idle_add(windows.manager.exit)

