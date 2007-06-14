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
from sugar.graphics.popupcontext import PopupContext
from sugar.activity import activityfactory
from sugar.datastore import datastore
from sugar import profile
import sugar

from view.ActivityHost import ActivityHost
from view.frame.frame import Frame
from view.keyhandler import KeyHandler
from view.home.HomeWindow import HomeWindow
from model import bundleregistry

from hardware import hardwaremanager

class Shell(gobject.GObject):
    def __init__(self, model):
        gobject.GObject.__init__(self)

        self._activities_starting = Set()
        self._model = model
        self._hosts = {}
        self._screen = wnck.screen_get_default()
        self._current_host = None
        self._screen_rotation = 0

        self._key_handler = KeyHandler(self)
        self._popup_context = PopupContext()

        self._frame = Frame(self)
        self._frame.show()

        self._home_window = HomeWindow(self)
        self._home_window.show()

        self._zoom_level = sugar.ZOOM_HOME

        home_model = self._model.get_home()
        home_model.connect('activity-started', self._activity_started_cb)
        home_model.connect('activity-removed', self._activity_removed_cb)
        home_model.connect('active-activity-changed',
                           self._active_activity_changed_cb)

        self.start_activity('org.laptop.JournalActivity')

        # Unfreeze the display when it's stable
        hw_manager = hardwaremanager.get_manager()
        hw_manager.set_dcon_freeze(0)

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

        if self._current_host:
            self._current_host.set_active(True)
            self.set_zoom_level(sugar.ZOOM_ACTIVITY)
        else:
            self.set_zoom_level(sugar.ZOOM_HOME)

    def get_model(self):
        return self._model

    def get_frame(self):
        return self._frame

    def get_popup_context(self):
        return self._popup_context

    def _join_error_cb(self, handler, err, home_model):
        logging.debug("Failed to join activity %s: %s" % (handler.get_activity_id(), err))
        home_model.notify_activity_launch_failed(handler.get_activity_id())

    def join_activity(self, bundle_id, activity_id):
        activity = self.get_activity(activity_id)
        if activity:
            activity.present()
            return

        # Get the service name for this activity, if
        # we have a bundle on the system capable of handling
        # this activity type
        breg = bundleregistry.get_registry()
        bundle = breg.get_bundle(bundle_id)
        if not bundle:
            logging.error("Couldn't find activity for type %s" % bundle_id)
            return

        home_model = self._model.get_home()
        home_model.notify_activity_launch(activity_id, bundle_id)

        handle = ActivityHandle(activity_id)
        handle.pservice_id = activity_id

        handler = activityfactory.create(bundle_id, handle)
        handler.connect('error', self._join_error_cb, home_model)

    def _start_error_cb(self, handler, err, home_model):
        home_model.notify_activity_launch_failed(handler.get_activity_id())

    def start_activity(self, activity_type):
        if activity_type in self._activities_starting:
            logging.debug("This activity is still launching.")
            return

        logging.debug('Trying to start activity of type %s' % activity_type)

        self._activities_starting.add(activity_type)
        try:
            handler = activityfactory.create(activity_type)

            home_model = self._model.get_home()
            home_model.notify_activity_launch(handler.get_activity_id(),
                                                activity_type)

            handler.connect('error', self._start_error_cb, home_model)
        except Exception, err:
            logging.debug("Couldn't start activity of type %s: %s" % (activity_type, err))
            self._activities_starting.remove(activity_type)

        # Zoom to Home for launch feedback
        self.set_zoom_level(sugar.ZOOM_HOME)

    def set_zoom_level(self, level):
        if self._zoom_level == level:
            return
        if len(self._hosts) == 0 and level == sugar.ZOOM_ACTIVITY:
            return

        self._zoom_level = level

        if self._zoom_level == sugar.ZOOM_ACTIVITY:
            self._screen.toggle_showing_desktop(False)
        else:
            self._screen.toggle_showing_desktop(True)
            self._home_window.set_zoom_level(self._zoom_level)

        if self._zoom_level == sugar.ZOOM_HOME:
            self._frame.show()
        else:
            self._frame.hide()

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
        width, height = window.get_size();
        x_orig, y_orig = window.get_origin();

        screenshot = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, has_alpha=False,
                                    bits_per_sample=8, width=width, height=height)
        screenshot.get_from_drawable(window, window.get_colormap(), x_orig, y_orig, 0, 0,
                                     width, height);
        screenshot.save(file_path, "png")

        jobject = datastore.create()
        jobject.metadata['title'] = _('Screenshot')
        jobject.metadata['keep'] = '0'
        jobject.metadata['buddies'] = ''
        jobject.metadata['preview'] = ''
        jobject.metadata['icon-color'] = profile.get_color().to_string()
        jobject.metadata['mime_type'] = 'image/png'
        jobject.file_path = file_path
        datastore.write(jobject)

