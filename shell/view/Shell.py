# Copyright (C) 2006-2007 Red Hat, Inc.
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

from gettext import gettext as _
from sets import Set
import logging
import tempfile
import os
import time

import gobject
import gtk
import wnck

from sugar.activity.activityhandle import ActivityHandle
from sugar import activity
from sugar.activity import activityfactory
from sugar.datastore import datastore
from sugar import profile
from sugar import env

from view.ActivityHost import ActivityHost
from view.frame.frame import Frame
from view.keyhandler import KeyHandler
from view.home.HomeWindow import HomeWindow
from model.shellmodel import ShellModel

class Shell(gobject.GObject):
    def __init__(self, model):
        gobject.GObject.__init__(self)

        self._activities_starting = Set()
        self._model = model
        self._hosts = {}
        self._screen = wnck.screen_get_default()
        self._current_host = None
        self._pending_host = None
        self._screen_rotation = 0

        self._key_handler = KeyHandler(self)

        self._frame = Frame(self)
        self._frame.show()

        self._home_window = HomeWindow(self)
        self._home_window.show()

        self._model.connect('notify::zoom-level',
                            self._zoom_level_changed_cb)

        home_model = self._model.get_home()
        home_model.connect('activity-started', self._activity_started_cb)
        home_model.connect('activity-removed', self._activity_removed_cb)
        home_model.connect('active-activity-changed',
                           self._active_activity_changed_cb)
        home_model.connect('pending-activity-changed',
                           self._pending_activity_changed_cb)

        gobject.idle_add(self._start_journal_idle)

    def _start_journal_idle(self):
        # Mount the datastore in internal flash
        datastore.mount(env.get_profile_path('datastore'), [])

        # Checking for the bundle existence will also ensure
        # that the shell service is started up.
        registry = activity.get_registry()
        if registry.get_activity('org.laptop.JournalActivity'):
            self.start_activity('org.laptop.JournalActivity')

    def _activity_started_cb(self, home_model, home_activity):
        activity_host = ActivityHost(home_activity)
        self._hosts[activity_host.get_xid()] = activity_host
        if home_activity.get_type() in self._activities_starting:
            self._activities_starting.remove(home_activity.get_type())

    def _activity_removed_cb(self, home_model, home_activity):
        if home_activity.get_type() in self._activities_starting:
            self._activities_starting.remove(home_activity.get_type())
        xid = home_activity.get_xid()
        if self._hosts.has_key(xid):
            self._hosts[xid].destroy()
            del self._hosts[xid]

    def _active_activity_changed_cb(self, home_model, home_activity):
        if home_activity:
            host = self._hosts[home_activity.get_xid()]
        else:
            host = None

        if self._current_host:
            self._current_host.set_active(False)

        self._current_host = host

    def _pending_activity_changed_cb(self, home_model, home_activity):
        if home_activity:
            self._pending_host = self._hosts[home_activity.get_xid()]
        else:
            self._pending_host = None

    def get_model(self):
        return self._model

    def get_frame(self):
        return self._frame

    def join_activity(self, bundle_id, activity_id):
        activity_host = self.get_activity(activity_id)
        if activity_host:
            activity_host.present()
            return

        # Get the service name for this activity, if
        # we have a bundle on the system capable of handling
        # this activity type
        registry = activity.get_registry()
        bundle = registry.get_activity(bundle_id)
        if not bundle:
            logging.error("Couldn't find activity for type %s" % bundle_id)
            return

        handle = ActivityHandle(activity_id)
        activityfactory.create(bundle_id, handle)

    def notify_launch(self, bundle_id, activity_id):
        # Zoom to Home for launch feedback
        self.set_zoom_level(ShellModel.ZOOM_HOME)

        home_model = self._model.get_home()
        home_model.notify_activity_launch(activity_id, bundle_id)

    def notify_launch_failure(self, activity_id):
        home_model = self._model.get_home()
        home_model.notify_activity_launch_failed(activity_id)

    def start_activity(self, activity_type):
        if activity_type in self._activities_starting:
            logging.debug("This activity is still launching.")
            return

        self._activities_starting.add(activity_type)
        activityfactory.create(activity_type)

    def _zoom_level_changed_cb(self, model, pspec):
        if model.get_zoom_level() == ShellModel.ZOOM_HOME:
            self._frame.show()
        else:
            self._frame.hide()

    def set_zoom_level(self, level):
        if level == self._model.get_zoom_level():
            return

        if level == ShellModel.ZOOM_ACTIVITY:
            if self._pending_host is not None:
                self._pending_host.present()
            self._screen.toggle_showing_desktop(False)
        else:
            self._model.set_zoom_level(level)
            self._screen.toggle_showing_desktop(True)
            self._home_window.set_zoom_level(level)

    def get_current_activity(self):
        return self._current_host

    def get_activity(self, activity_id):
        for host in self._hosts.values():
            if host.get_id() == activity_id:
                return host
        return None

    def toggle_chat_visibility(self):
        act = self.get_current_activity()
        if not act:
            return
        is_visible = self._frame.is_visible()
        if act.is_chat_visible():
            frame_was_visible = act.chat_hide()
            if not frame_was_visible:
                self._frame.do_slide_out()
        else:
            if not is_visible:
                self._frame.do_slide_in()
            act.chat_show(is_visible)

    def take_screenshot(self):
        file_path = os.path.join(tempfile.gettempdir(), '%i' % time.time())

        window = gtk.gdk.get_default_root_window()
        width, height = window.get_size()
        x_orig, y_orig = window.get_origin()

        screenshot = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, has_alpha=False,
                                    bits_per_sample=8, width=width, height=height)
        screenshot.get_from_drawable(window, window.get_colormap(), x_orig, y_orig, 0, 0,
                                     width, height)
        screenshot.save(file_path, "png")
        try:
            jobject = datastore.create()
            try:
                jobject.metadata['title'] = _('Screenshot')
                jobject.metadata['keep'] = '0'
                jobject.metadata['buddies'] = ''
                jobject.metadata['preview'] = ''
                jobject.metadata['icon-color'] = profile.get_color().to_string()
                jobject.metadata['mime_type'] = 'image/png'
                jobject.file_path = file_path
                datastore.write(jobject)
            finally:
                jobject.destroy()
                del jobject
        finally:
            os.remove(file_path)

