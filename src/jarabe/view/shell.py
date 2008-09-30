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
import logging
import tempfile
import os
import time
import shutil

import gobject
import gtk
import wnck
import dbus

from sugar.activity.activityhandle import ActivityHandle
from sugar import activity
from sugar.activity import activityfactory
from sugar.datastore import datastore
from sugar import profile
from sugar import env

from jarabe.view.activityhost import ActivityHost
from jarabe.view.launchwindow import LaunchWindow
from jarabe.model import shellmodel
from jarabe.journal import journalactivity

class Shell(gobject.GObject):
    def __init__(self):
        gobject.GObject.__init__(self)

        self._model = shellmodel.get_instance()
        self._hosts = {}
        self._launchers = {}
        self._screen = wnck.screen_get_default()
        self._screen_rotation = 0

        from jarabe.view.keyhandler import KeyHandler
        self._key_handler = KeyHandler()

        from jarabe.frame import frame
        self._frame = frame.get_instance()

        from jarabe.desktop.homewindow import HomeWindow
        self.home_window = HomeWindow()
        self.home_window.show()

        home_model = self._model.get_home()
        home_model.connect('launch-started', self.__launch_started_cb)
        home_model.connect('launch-failed', self.__launch_failed_cb)
        home_model.connect('launch-completed', self.__launch_completed_cb)
        home_model.connect('activity-removed', self._activity_removed_cb)

        gobject.idle_add(self._start_journal_idle)

    def _start_journal_idle(self):
        # Mount the datastore in internal flash
        ds_path = env.get_profile_path('datastore')
        try:
            datastore.mount(ds_path, [], timeout=120)
        except Exception, e:
            # Don't explode if there's corruption; move the data out of the way
            # and attempt to create a store from scratch.
            logging.error(e)
            shutil.move(ds_path, os.path.abspath(ds_path) + str(time.time()))
            datastore.mount(ds_path, [], timeout=120)

        journalactivity.start()

    def __launch_started_cb(self, home_model, home_activity):
        if home_activity.is_journal():
            return

        launch_window = LaunchWindow(home_activity)
        launch_window.show()

        self._launchers[home_activity.get_activity_id()] = launch_window
        self._model.set_zoom_level(shellmodel.ShellModel.ZOOM_ACTIVITY)

    def __launch_failed_cb(self, home_model, home_activity):
        if not home_activity.is_journal():
            self._destroy_launcher(home_activity)

    def __launch_completed_cb(self, home_model, home_activity):
        activity_host = ActivityHost(home_activity)
        self._hosts[activity_host.get_xid()] = activity_host

        if not home_activity.is_journal():
            self._destroy_launcher(home_activity)

    def _destroy_launcher(self, home_activity):
        activity_id = home_activity.get_activity_id()

        if activity_id in self._launchers:
            self._launchers[activity_id].destroy()
            del self._launchers[activity_id]
        else:
            logging.error('Launcher for %s is missing' % activity_id)

    def _activity_removed_cb(self, home_model, home_activity):
        xid = home_activity.get_xid()
        if self._hosts.has_key(xid):
            del self._hosts[xid]

    def _get_host_from_activity_model(self, activity_model):
        if activity_model is None:
            raise ValueError('activity_model cannot be None')
        xid = activity_model.get_xid()
        if xid:
            return self._hosts[activity_model.get_xid()]
        else:
            logging.debug('Activity %r dont have a window yet' % activity_model)
            return None

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

    def start_activity(self, activity_type):
        activityfactory.create(activity_type)

    def start_activity_with_uri(self, activity_type, uri):
        activityfactory.create_with_uri(activity_type, uri)

    def take_activity_screenshot(self):
        if self._model.get_zoom_level() != shellmodel.ShellModel.ZOOM_ACTIVITY:
            return
        if self.get_frame().visible:
            return

        home_model = self._model.get_home()
        active_activity = home_model.get_active_activity()
        if active_activity is not None:
            service = active_activity.get_service()
            if service is not None:
                try:
                    service.TakeScreenshot(timeout=2.0)
                except dbus.DBusException, e:
                    logging.debug('Error raised by TakeScreenshot(): %s', e)

    def set_zoom_level(self, level):
        if level == self._model.get_zoom_level():
            logging.debug('Already in the level %r' % level)
            return

        if level == shellmodel.ShellModel.ZOOM_ACTIVITY:
            host = self.get_current_activity()
            if host is None:
                raise ValueError('No current activity')
            host.present()
        else:
            self._model.set_zoom_level(level)
            self._screen.toggle_showing_desktop(True)

    def toggle_activity_fullscreen(self):
        if self._model.get_zoom_level() == shellmodel.ShellModel.ZOOM_ACTIVITY:
            self.get_current_activity().toggle_fullscreen()

    def activate_previous_activity(self):
        home_model = self._model.get_home()
        previous_activity = home_model.get_previous_activity()
        if previous_activity:
            previous_activity.get_window().activate(
						gtk.get_current_event_time())

    def activate_next_activity(self):
        home_model = self._model.get_home()
        next_activity = home_model.get_next_activity()
        if next_activity:
            next_activity.get_window().activate(gtk.get_current_event_time())

    def close_current_activity(self):
        if self._model.get_zoom_level() != shellmodel.ShellModel.ZOOM_ACTIVITY:
            return

        home_model = self._model.get_home()
        active_activity = home_model.get_active_activity()
        if active_activity.is_journal():
            return

        self.get_current_activity().close()

    def get_current_activity(self):
        home_model = self._model.get_home()
        active_activity = home_model.get_active_activity()
        return self._get_host_from_activity_model(active_activity)

    def get_activity(self, activity_id):
        for host in self._hosts.values():
            if host.get_id() == activity_id:
                return host
        return None

    def take_screenshot(self):
        file_path = os.path.join(tempfile.gettempdir(), '%i' % time.time())

        window = gtk.gdk.get_default_root_window()
        width, height = window.get_size()
        x_orig, y_orig = window.get_origin()

        screenshot = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, has_alpha=False,
                                    bits_per_sample=8, width=width,
                                    height=height)
        screenshot.get_from_drawable(window, window.get_colormap(), x_orig,
                                     y_orig, 0, 0, width, height)
        screenshot.save(file_path, "png")
        jobject = datastore.create()
        try:
            jobject.metadata['title'] = _('Screenshot')
            jobject.metadata['keep'] = '0'
            jobject.metadata['buddies'] = ''
            jobject.metadata['preview'] = ''
            jobject.metadata['icon-color'] = profile.get_color().to_string()
            jobject.metadata['mime_type'] = 'image/png'
            jobject.file_path = file_path
            datastore.write(jobject, transfer_ownership=True)
        finally:
            jobject.destroy()
            del jobject

_instance = None

def get_instance():
    global _instance
    if not _instance:
        _instance = Shell()
    return _instance

