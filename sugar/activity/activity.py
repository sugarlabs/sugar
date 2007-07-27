"""Base class for Python-coded activities

This is currently the only reference for what an 
activity must do to participate in the Sugar desktop.
"""
# Copyright (C) 2006-2007 Red Hat, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

from gettext import gettext as _
import logging
import os
import time
import tempfile

import gtk, gobject
import dbus

from sugar import util        
from sugar.presence import presenceservice
from sugar.activity.activityservice import ActivityService
from sugar.graphics import units
from sugar.graphics.window import Window
from sugar.graphics.toolbox import Toolbox
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.toolcombobox import ToolComboBox
from sugar.datastore import datastore
from sugar import wm
from sugar import profile
from sugar import _sugaruiext

class ActivityToolbar(gtk.Toolbar):
    SHARE_PRIVATE = 0
    SHARE_NEIGHBORHOOD = 1

    def __init__(self, activity):
        gtk.Toolbar.__init__(self)

        self._activity = activity
        activity.connect('shared', self._activity_shared_cb)
        activity.connect('joined', self._activity_shared_cb)

        if activity.metadata:
            self.title = gtk.Entry()
            self.title.set_size_request(int(gtk.gdk.screen_width() / 6), -1)
            self.title.set_text(activity.metadata['title'])
            self.title.connect('changed', self._title_changed_cb)
            self._add_widget(self.title)

            activity.metadata.connect('updated', self._jobject_updated_cb)

        separator = gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True);
        self.insert(separator, -1)
        separator.show()

        self.share = ToolComboBox(label_text='Share with:')
        self.share.combo.connect('changed', self._share_changed_cb)
        self.share.combo.append_item(None, _('Private'),
                                     'theme:zoom-home-mini')
        self.share.combo.append_item(None, _('My Neighborhood'),
                                     'theme:zoom-neighborhood-mini')
        self._update_share()

        self.insert(self.share, -1)
        self.share.show()

        self.keep = ToolButton('document-save')
        self.keep.set_tooltip(_('Keep'))
        self.keep.connect('clicked', self._keep_clicked_cb)
        self.insert(self.keep, -1)
        self.keep.show()

        self.stop = ToolButton('activity-stop')
        self.stop.set_tooltip(_('Stop'))
        self.stop.connect('clicked', self._stop_clicked_cb)
        self.insert(self.stop, -1)
        self.stop.show()

        self._update_title_sid = None

    def _update_share(self):
        if self._activity.get_shared():
            self.share.set_sensitive(False)
            self.share.combo.set_active(self.SHARE_NEIGHBORHOOD)
        else:
            self.share.set_sensitive(True)
            self.share.combo.set_active(self.SHARE_PRIVATE)
    
    def _share_changed_cb(self, combo):
        if self.share.combo.get_active() == self.SHARE_NEIGHBORHOOD:
            self._activity.share()

    def _keep_clicked_cb(self, button):
        self._activity.save()

    def _stop_clicked_cb(self, button):
        self._activity.close()
        self._activity.destroy()

    def _jobject_updated_cb(self, jobject):
        self.title.set_text(jobject['title'])

    def _title_changed_cb(self, entry):
        if not self._update_title_sid:
            self._update_title_sid = gobject.timeout_add(1000, self._update_title_cb)

    def _update_title_cb(self):
        self._activity.metadata['title'] = self.title.get_text()
        self._activity.metadata['title_set_by_user'] = '1'
        self._activity.save()
        self._update_title_sid = None
        return False

    def _add_widget(self, widget, expand=False):
        tool_item = gtk.ToolItem()
        tool_item.set_expand(expand)

        tool_item.add(widget)
        widget.show()

        self.insert(tool_item, -1)
        tool_item.show()

    def _activity_shared_cb(self, activity):
        self._update_share()

class EditToolbar(gtk.Toolbar):
    def __init__(self):
        gtk.Toolbar.__init__(self)

        self.undo = ToolButton('edit-undo')
        self.insert(self.undo, -1)
        self.undo.show()

        self.redo = ToolButton('edit-redo')
        self.insert(self.redo, -1)
        self.redo.show()

        separator = gtk.SeparatorToolItem()
        separator.set_draw(True)
        self.insert(separator, -1)
        separator.show()

        self.copy = ToolButton('edit-copy')
        self.insert(self.copy, -1)
        self.copy.show()

        self.paste = ToolButton('edit-paste')
        self.insert(self.paste, -1)
        self.paste.show()

class ActivityToolbox(Toolbox):
    def __init__(self, activity):
        Toolbox.__init__(self)
        
        self._activity_toolbar = ActivityToolbar(activity)
        self.add_toolbar('Activity', self._activity_toolbar)
        self._activity_toolbar.show()

    def get_activity_toolbar(self):
        return self._activity_toolbar

class Activity(Window, gtk.Container):
    """Base Activity class that all other Activities derive from."""
    __gtype_name__ = 'SugarActivity'

    __gsignals__ = {
        'shared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
        'joined': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([]))
    }

    __gproperties__ = {
        'active': (bool, None, None, False, gobject.PARAM_READWRITE)
    }

    def __init__(self, handle, create_jobject=True):
        """Initialise the Activity 
        
        handle -- sugar.activity.activityhandle.ActivityHandle
            instance providing the activity id and access to the 
            presence service which *may* provide sharing for this 
            application

        create_jobject -- boolean
            define if it should create a journal object if we are
            not resuming

        Side effects: 
        
            Sets the gdk screen DPI setting (resolution) to the 
            Sugar screen resolution.
            
            Connects our "destroy" message to our _destroy_cb
            method.
        
            Creates a base gtk.Window within this window.
            
            Creates an ActivityService (self._bus) servicing
            this application.
        """
        Window.__init__(self)

        # process titles will only show 15 characters
        # but they get truncated anyway so if more characters
        # are supported in the future we will get a better view
        # of the processes
        proc_title = "%s <%s>" % (get_bundle_name(), handle.activity_id)
        util.set_proc_title(proc_title)

        self.connect('realize', self._realize_cb)
        self.connect('delete-event', self._delete_event_cb)

        self._active = False
        self._activity_id = handle.activity_id
        self._pservice = presenceservice.get_instance()
        self._shared_activity = None
        self._share_id = None
        self._join_id = None
        self._can_close = True
        self._preview = None
        self._updating_jobject = False
        self._closing = False

        shared_activity = handle.get_shared_activity()
        if shared_activity:
            # Join an existing instance of this activity on the network
            self._shared_activity = shared_activity
            self._join_id = self._shared_activity.connect("joined", self._internal_joined_cb)
            if not self._shared_activity.props.joined:
                self._shared_activity.join()
            else:
                self._internal_joined_cb(self._shared_activity, True, None)

        self._bus = ActivityService(self)
        self._owns_file = False

        if handle.object_id:
            self._jobject = datastore.get(handle.object_id)
            # TODO: Don't create so many objects until we have versioning
            # support in the datastore
            #self._jobject.object_id = ''
            #del self._jobject.metadata['ctime']
            del self._jobject.metadata['mtime']
        elif create_jobject:
            logging.debug('Creating a jobject.')
            self._jobject = datastore.create()
            self._jobject.metadata['title'] = _('%s Activity') % get_bundle_name()
            self._jobject.metadata['title_set_by_user'] = '0'
            self._jobject.metadata['activity'] = self.get_service_name()
            self._jobject.metadata['activity_id'] = self.get_id()
            self._jobject.metadata['keep'] = '0'
            #self._jobject.metadata['buddies'] = ''
            self._jobject.metadata['preview'] = ''
            self._jobject.metadata['icon-color'] = profile.get_color().to_string()
            self._jobject.file_path = ''
            datastore.write(self._jobject,
                    reply_handler=self._internal_jobject_create_cb,
                    error_handler=self._internal_jobject_error_cb)
        else:
            self._jobject = None

    def do_set_property(self, pspec, value):
        if pspec.name == 'active':
            if self._active != value:
                self._active = value
                if not self._active and self._jobject:
                    self.save()

    def do_get_property(self, pspec):
        if pspec.name == 'active':
            return self._active

    def get_id(self):
        return self._activity_id

    def get_service_name(self):
        return _sugaruiext.get_prgname()

    def set_canvas(self, canvas):
        Window.set_canvas(self, canvas)
        canvas.connect('map', self._canvas_map_cb)

    def _canvas_map_cb(self, canvas):
        if self._jobject and self._jobject.file_path:
            self.read_file(self._jobject.file_path)

    def _internal_jobject_create_cb(self):
        pass

    def _internal_jobject_error_cb(self, err):
        logging.debug("Error creating activity datastore object: %s" % err)

    def read_file(self, file_path):
        """
        Subclasses implement this method if they support resuming objects from
        the journal. 'file_path' is the file to read from.
        """
        raise NotImplementedError

    def write_file(self, file_path):
        """
        Subclasses implement this method if they support saving data to objects
        in the journal. 'file_path' is the file to write to.
        """
        raise NotImplementedError

    def _internal_save_cb(self):
        self._updating_jobject = False
        if self._closing:
            self._cleanup_jobject()
            self.destroy()

    def _internal_save_error_cb(self, err):
        self._updating_jobject = False
        if self._closing:
            self._cleanup_jobject()
            self.destroy()
        logging.debug("Error saving activity object to datastore: %s" % err)

    def _cleanup_jobject(self):
        if self._jobject:
            if self._owns_file and os.path.isfile(self._jobject.file_path):
                logging.debug('_cleanup_jobject: removing %r' % self._jobject.file_path)
                os.remove(self._jobject.file_path)
            self._owns_file = False
            self._jobject.destroy()
            self._jobject = None

    def _get_preview(self):
        preview_pixbuf = self.get_canvas_screenshot()
        if preview_pixbuf is None:
            return None
        preview_pixbuf = preview_pixbuf.scale_simple(units.grid_to_pixels(4),
                                                     units.grid_to_pixels(3),
                                                     gtk.gdk.INTERP_BILINEAR)

        # TODO: Find a way of taking a png out of the pixbuf without saving to a temp file.
        #       Impementing gtk.gdk.Pixbuf.save_to_buffer in pygtk would solve this.
        fd, file_path = tempfile.mkstemp('.png')
        del fd
        preview_pixbuf.save(file_path, 'png')
        f = open(file_path)
        try:
            preview_data = f.read()
        finally:
            f.close()
            os.remove(file_path)

        # TODO: Take this out when the datastore accepts binary data.        
        import base64
        return base64.b64encode(preview_data)

    def _get_buddies(self):
        return ''

    def save(self):
        """Request that the activity is saved to the Journal."""

        if self._updating_jobject:
            return

        #self.metadata['buddies'] = self._get_buddies()
        if self._preview is None:
            self.metadata['preview'] = ''
        else:
            self.metadata['preview'] = self._preview
        try:
            if self._jobject.file_path:
                self.write_file(self._jobject.file_path)
            else:
                file_path = os.path.join(tempfile.gettempdir(), '%i' % time.time())
                self.write_file(file_path)
                self._owns_file = True
                self._jobject.file_path = file_path
        except NotImplementedError:
            pass
        self._updating_jobject = True
        datastore.write(self._jobject,
                reply_handler=self._internal_save_cb,
                error_handler=self._internal_save_error_cb)

    def _internal_joined_cb(self, activity, success, err):
        """Callback when join has finished"""
        self._shared_activity.disconnect(self._join_id)
        self._join_id = None
        if not success:
            logging.debug("Failed to join activity: %s" % err)
            return
        self.present()
        self.emit('joined')

    def get_shared(self):
        """Returns TRUE if the activity is shared on the mesh."""
        if not self._shared_activity:
            return False
        return self._shared_activity.props.joined

    def _internal_share_cb(self, ps, success, activity, err):
        self._pservice.disconnect(self._share_id)
        self._share_id = None
        if not success:
            logging.debug('Share of activity %s failed: %s.' % (self._activity_id, err))
            return
        logging.debug('Share of activity %s successful.' % self._activity_id)
        self._shared_activity = activity
        self.emit('shared')

    def share(self):
        """Request that the activity be shared on the network."""
        if self._shared_activity and self._shared_activity.props.joined:
            raise RuntimeError("Activity %s already shared." % self._activity_id)
        logging.debug('Requesting share of activity %s.' % self._activity_id)
        self._share_id = self._pservice.connect("activity-shared", self._internal_share_cb)
        self._pservice.share_activity(self)

    def _realize_cb(self, window):
        wm.set_bundle_id(window.window, self.get_service_name())
        wm.set_activity_id(window.window, self._activity_id)

    def _delete_event_cb(self, window, event):
        if self._can_close:
            self.close()
            return False
        else:
            return True

    def close(self):
        self._closing = True

        if self._bus:
            del self._bus
            self._bus = None
        if self._shared_activity:
            self._shared_activity.leave()

        self._preview = self._get_preview()
        self.save()

    def destroy(self):
        if self._updating_jobject:
            # Delay destruction
            self.hide()
        else:
            Window.destroy(self)

    def get_metadata(self):
        if self._jobject:
            return self._jobject.metadata
        else:
            return None

    metadata = property(get_metadata, None)

def get_bundle_name():
    """Return the bundle name for the current process' bundle
    """
    return _sugaruiext.get_application_name()
    
def get_bundle_path():
    """Return the bundle path for the current process' bundle
    """
    return os.environ['SUGAR_BUNDLE_PATH']

