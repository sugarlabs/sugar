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
from hashlib import sha1

import gtk, gobject
import dbus
import json

from sugar import util        
from sugar.presence import presenceservice
from sugar.activity.activityservice import ActivityService
from sugar.graphics import style
from sugar.graphics.window import Window
from sugar.graphics.toolbox import Toolbox
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.toolcombobox import ToolComboBox
from sugar.datastore import datastore
from sugar import wm
from sugar import profile
from sugar import _sugarext

SCOPE_PRIVATE = "private"
SCOPE_INVITE_ONLY = "invite"  # shouldn't be shown in UI, it's implicit when you invite somebody
SCOPE_NEIGHBORHOOD = "public"

class ActivityToolbar(gtk.Toolbar):
    def __init__(self, activity):
        gtk.Toolbar.__init__(self)

        self._activity = activity
        activity.connect('shared', self._activity_shared_cb)
        activity.connect('joined', self._activity_shared_cb)
        activity.connect('notify::max_participants',
                         self._max_participants_changed_cb)

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

        self.share = ToolComboBox(label_text=_('Share with:'))
        self.share.combo.connect('changed', self._share_changed_cb)
        self.share.combo.append_item(SCOPE_PRIVATE, _('Private'),
                                     'zoom-home-mini')
        self.share.combo.append_item(SCOPE_NEIGHBORHOOD, _('My Neighborhood'),
                                     'zoom-neighborhood-mini')
        self.insert(self.share, -1)
        self.share.show()

        self._update_share()

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
        if self._activity.props.max_participants == 1:
            self.share.hide()

        if self._activity.get_shared():
            self.share.set_sensitive(False)
            self.share.combo.set_active(1)
        else:
            self.share.set_sensitive(True)
            self.share.combo.set_active(0)
    
    def _share_changed_cb(self, combo):
        if not self.props.sensitive:
            # Ignore programmatic combo changes, only respond
            # to user-initiated ones
            return
        model = self.share.combo.get_model()
        it = self.share.combo.get_active_iter()
        (scope, ) = model.get(it, 0)
        if scope == SCOPE_NEIGHBORHOOD:
            self._activity.share()
        elif scope == SCOPE_INVITE_ONLY:
            self._activity.share(private=True)

    def _keep_clicked_cb(self, button):
        self._activity.copy()

    def _stop_clicked_cb(self, button):
        self._activity.close()
        self._activity.destroy()

    def _jobject_updated_cb(self, jobject):
        self.title.set_text(jobject['title'])

    def _title_changed_cb(self, entry):
        if not self._update_title_sid:
            self._update_title_sid = gobject.timeout_add(1000, self._update_title_cb)

    def _update_title_cb(self):
        title = self.title.get_text()

        self._activity.metadata['title'] = title
        self._activity.metadata['title_set_by_user'] = '1'
        self._activity.save()

        shared_activity = self._activity._shared_activity
        if shared_activity:
            shared_activity.props.name = title

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

    def _max_participants_changed_cb(self, activity, pspec):
        self._update_share()

class EditToolbar(gtk.Toolbar):
    def __init__(self):
        gtk.Toolbar.__init__(self)

        self.undo = ToolButton('edit-undo')
        self.undo.set_tooltip(_('Undo'))
        self.insert(self.undo, -1)
        self.undo.show()

        self.redo = ToolButton('edit-redo')
        self.redo.set_tooltip(_('Redo'))
        self.insert(self.redo, -1)
        self.redo.show()

        self.separator = gtk.SeparatorToolItem()
        self.separator.set_draw(True)
        self.insert(self.separator, -1)
        self.separator.show()

        self.copy = ToolButton('edit-copy')
        self.copy.set_tooltip(_('Copy'))
        self.insert(self.copy, -1)
        self.copy.show()

        self.paste = ToolButton('edit-paste')
        self.copy.set_tooltip(_('Paste'))
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
        'active'          : (bool, None, None, False,
                             gobject.PARAM_READWRITE),
        'max-participants': (int, None, None, 0, 1000, 0,
                             gobject.PARAM_READWRITE)
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
        self._max_participants = 0

        self._bus = ActivityService(self)
        self._owns_file = False

        share_scope = SCOPE_PRIVATE

        if handle.object_id:
            self._jobject = datastore.get(handle.object_id)
            # TODO: Don't create so many objects until we have versioning
            # support in the datastore
            #self._jobject.object_id = ''
            #del self._jobject.metadata['ctime']
            del self._jobject.metadata['mtime']

            if not self._jobject.metadata.has_key('title'):
                self._jobject.metadata['title'] = ''

            try:
                share_scope = self._jobject.metadata['share-scope']
                title = self._jobject.metadata['title']
                self.set_title(title)
            except KeyError:
                pass
        elif create_jobject:
            logging.debug('Creating a jobject.')
            self._jobject = datastore.create()
            self._jobject.metadata['title'] = _('%s Activity') % get_bundle_name()
            self.set_title(self._jobject.metadata['title'])
            self._jobject.metadata['title_set_by_user'] = '0'
            self._jobject.metadata['activity'] = self.get_service_name()
            self._jobject.metadata['activity_id'] = self.get_id()
            self._jobject.metadata['keep'] = '0'
            self._jobject.metadata['preview'] = ''
            self._jobject.metadata['share-scope'] = SCOPE_PRIVATE

            if self._shared_activity is not None:
                icon_color = self._shared_activity.props.color
            else:
                icon_color = profile.get_color().to_string()

            self._jobject.metadata['icon-color'] = icon_color

            self._jobject.file_path = ''
            datastore.write(self._jobject,
                    reply_handler=self._internal_jobject_create_cb,
                    error_handler=self._internal_jobject_error_cb)
        else:
            self._jobject = None

        # handle activity share/join
        mesh_instance = self._pservice.get_activity(self._activity_id)
        logging.debug("*** Act %s, mesh instance %r, scope %s" % (self._activity_id, mesh_instance, share_scope))
        if mesh_instance:
            # There's already an instance on the mesh, join it
            logging.debug("*** Act %s joining existing mesh instance" % self._activity_id)
            self._shared_activity = mesh_instance
            self._join_id = self._shared_activity.connect("joined", self._internal_joined_cb)
            if not self._shared_activity.props.joined:
                self._shared_activity.join()
            else:
                self._internal_joined_cb(self._shared_activity, True, None)
        elif share_scope != SCOPE_PRIVATE:
            logging.debug("*** Act %s no existing mesh instance, but used to be shared, will share" % self._activity_id)
            # no existing mesh instance, but activity used to be shared, so
            # restart the share
            if share_scope == SCOPE_INVITE_ONLY:
                self.share(private=True)
            elif share_scope == SCOPE_NEIGHBORHOOD:
                self.share(private=False)
            else:
                logging.debug("Unknown share scope %r" % share_scope)

    def do_set_property(self, pspec, value):
        if pspec.name == 'active':
            if self._active != value:
                self._active = value
                if not self._active and self._jobject:
                    self.save()
        elif pspec.name == 'max-participants':
            self._max_participants = value

    def do_get_property(self, pspec):
        if pspec.name == 'active':
            return self._active
        elif pspec.name == 'max-participants':
            return self._max_participants

    def get_id(self):
        return self._activity_id

    def get_service_name(self):
        return _sugarext.get_prgname()

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

    def get_activity_root(self):
        """
        Return the appropriate location in the fs where to store activity related
        data that doesn't pertain to the current execution of the activity and
        thus cannot go into the DataStore.
        """
        if os.environ.has_key('SUGAR_ACTIVITY_ROOT') and \
           os.environ['SUGAR_ACTIVITY_ROOT']:
            return os.environ['SUGAR_ACTIVITY_ROOT']
        else:
            return '/'

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
        preview_pixbuf = preview_pixbuf.scale_simple(style.zoom(300),
                                                     style.zoom(225),
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
        if self._shared_activity is not None:
            buddies = {}
            for buddy in self._shared_activity.get_joined_buddies():
                if not buddy.props.owner:
                    buddy_id = sha1(buddy.props.key).hexdigest()
                    buddies[buddy_id] = [buddy.props.nick, buddy.props.color]
            return buddies
        else:
            return {}

    def save(self):
        """Request that the activity is saved to the Journal."""

        logging.debug('Activity.save: %r' % self._jobject.object_id)

        if self._updating_jobject:
            return

        buddies_dict = self._get_buddies()
        if buddies_dict:
            self.metadata['buddies_id'] = json.write(buddies_dict.keys())
            self.metadata['buddies'] = json.write(self._get_buddies())

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
                transfer_ownership=True,
                reply_handler=self._internal_save_cb,
                error_handler=self._internal_save_error_cb)

    def copy(self):
        logging.debug('Activity.copy: %r' % self._jobject.object_id)
        self.save()
        self._jobject.object_id = None

    def _internal_joined_cb(self, activity, success, err):
        """Callback when join has finished"""
        self._shared_activity.disconnect(self._join_id)
        self._join_id = None
        if not success:
            logging.debug("Failed to join activity: %s" % err)
            return
        self.present()
        self.emit('joined')
        if self._jobject:
            # FIXME: some way to distinguish between share scopes
            self._jobject.metadata['share-scope'] = SCOPE_NEIGHBORHOOD

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

        activity.props.name = self._jobject.metadata['title']

        self._shared_activity = activity
        self.emit('shared')
        if self._jobject:
            # FIXME: some way to distinguish between share scopes
            self._jobject.metadata['share-scope'] = SCOPE_NEIGHBORHOOD

    def share(self, private=False):
        """Request that the activity be shared on the network.
        
        private -- bool: True to share by invitation only,
            False to advertise as shared to everyone.

        Once the activity is shared, its privacy can be changed by setting
        its 'private' property.
        """
        # FIXME: Make private=True to turn on the by-invitation-only scope
        if self._shared_activity and self._shared_activity.props.joined:
            raise RuntimeError("Activity %s already shared." %
                               self._activity_id)
        verb = private and 'private' or 'public'
        logging.debug('Requesting %s share of activity %s.' %
                      (verb, self._activity_id))
        self._share_id = self._pservice.connect("activity-shared", 
                                                self._internal_share_cb)
        self._pservice.share_activity(self, private=private)

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
    return _sugarext.get_application_name()
    
def get_bundle_path():
    """Return the bundle path for the current process' bundle
    """
    return os.environ['SUGAR_BUNDLE_PATH']

