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

import gtk
import logging

from jarabe.view import OverlayWindow

class ActivityHost:
    def __init__(self, model):
        self._model = model
        self._window = model.get_window()
        self._gdk_window = gtk.gdk.window_foreign_new(self.get_xid())

        try:
            self._overlay_window = OverlayWindow.OverlayWindow(self._gdk_window)
        except RuntimeError:
            self._overlay_window = None

    def get_id(self):
        return self._model.get_activity_id()

    def get_xid(self):
        return self._window.get_xid()

    def get_model(self):
        return self._model

    def invite(self, buddy_model):
        service = self._model.get_service()
        if service:
            buddy = buddy_model.get_buddy()
            service.Invite(buddy.props.key)
        else:
            logging.error('Invite failed, activity service not ')

    def toggle_fullscreen(self):
        fullscreen = not self._window.is_fullscreen()
        self._window.set_fullscreen(fullscreen)

    def present(self):
        self._window.activate(gtk.get_current_event_time())

    def close(self):
        # The "1" is a fake timestamp as with present()
        self._window.close(1)

    def show_dialog(self, dialog):
        dialog.show()
        dialog.window.set_transient_for(self._gdk_window)
