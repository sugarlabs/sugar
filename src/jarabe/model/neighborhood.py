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

import gobject
import gconf
import logging

from sugar.graphics.xocolor import XoColor
from sugar.presence import presenceservice
from sugar import activity

from jarabe.model.buddy import BuddyModel
from jarabe.model import bundleregistry
from jarabe.util.telepathy import connection_watcher

from dbus import PROPERTIES_IFACE
from telepathy.interfaces import CONNECTION_INTERFACE_REQUESTS

CONN_INTERFACE_GADGET = 'org.laptop.Telepathy.Gadget'
CHAN_INTERFACE_VIEW = 'org.laptop.Telepathy.Channel.Interface.View'
CHAN_INTERFACE_BUDBY_VIEW = 'org.laptop.Telepathy.Channel.Type.BuddyView'
CHAN_INTERFACE_ACTIVITY_VIEW = 'org.laptop.Telepathy.Channel.Type.ActivityView'

NB_RANDOM_BUDDIES = 20
NB_RANDOM_ACTIVITIES = 40

class ActivityModel:
    def __init__(self, act, bundle):
        self.activity = act
        self.bundle = bundle

    def get_id(self):
        return self.activity.props.id
        
    def get_icon_name(self):
        return self.bundle.get_icon()
    
    def get_color(self):
        return XoColor(self.activity.props.color)

    def get_bundle_id(self):
        return self.bundle.get_bundle_id()

class Neighborhood(gobject.GObject):
    __gsignals__ = {
        'activity-added':       (gobject.SIGNAL_RUN_FIRST,
                                 gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT])),
        'activity-removed':     (gobject.SIGNAL_RUN_FIRST,
                                 gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT])),
        'buddy-added':          (gobject.SIGNAL_RUN_FIRST,
                                 gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT])),
        'buddy-moved':          (gobject.SIGNAL_RUN_FIRST,
                                 gobject.TYPE_NONE,
                                ([gobject.TYPE_PYOBJECT,
                                  gobject.TYPE_PYOBJECT])),
        'buddy-removed':        (gobject.SIGNAL_RUN_FIRST,
                                 gobject.TYPE_NONE, ([gobject.TYPE_PYOBJECT]))
    }

    def __init__(self):
        gobject.GObject.__init__(self)

        self._activities = {}
        self._buddies = {}

        self._pservice = presenceservice.get_instance()
        self._pservice.connect("activity-appeared",
                               self._activity_appeared_cb)
        self._pservice.connect('activity-disappeared',
                               self._activity_disappeared_cb)
        self._pservice.connect("buddy-appeared",
                               self._buddy_appeared_cb)
        self._pservice.connect("buddy-disappeared",
                               self._buddy_disappeared_cb)

        # Add any buddies the PS knows about already
        self._pservice.get_buddies_async(reply_handler=self._get_buddies_cb)

        self._pservice.get_activities_async(
                reply_handler=self._get_activities_cb)

        self._conn_watcher = connection_watcher.ConnectionWatcher()
        self._conn_watcher.connect('connection-added', self.__conn_addded_cb)

        for conn in self._conn_watcher.get_connections():
            self.__conn_addded_cb(self._conn_watcher, conn)

        self.gconf_client = gconf.client_get_default()
        self.gconf_client.add_dir('/desktop/sugar/collaboration', gconf.CLIENT_PRELOAD_NONE)
        self.gconf_client.notify_add('/desktop/sugar/collaboration/publish_gadget',
            self.__publish_gadget_changed_cb)

    def __conn_addded_cb(self, watcher, conn):
        if CONN_INTERFACE_GADGET not in conn:
            return

        conn[CONN_INTERFACE_GADGET].connect_to_signal('GadgetDiscovered',
                lambda: self._gadget_discovered(conn))

        gadget_discovered = conn[PROPERTIES_IFACE].Get(CONN_INTERFACE_GADGET,
                'GadgetAvailable')
        if gadget_discovered:
            self._gadget_discovered(conn)

    def _gadget_discovered(self, conn):
        publish = self.gconf_client.get_bool('/desktop/sugar/collaboration/publish_gadget')
        logging.debug("Gadget discovered on connection %s."
                " Publish our status: %r" %
                (conn.service_name.split('.')[-1], publish))
        conn[CONN_INTERFACE_GADGET].Publish(publish)

        self._request_random_buddies(conn, NB_RANDOM_BUDDIES)
        self._request_random_activities(conn, NB_RANDOM_ACTIVITIES)

    def _request_random_buddies(self, conn, nb):
        logging.debug("Request %d random buddies" % nb)

        conn[CONNECTION_INTERFACE_REQUESTS].CreateChannel(
            { 'org.freedesktop.Telepathy.Channel.ChannelType':
                'org.laptop.Telepathy.Channel.Type.BuddyView',
               'org.laptop.Telepathy.Channel.Interface.View.MaxSize': nb
          })

    def _request_random_activities(self, conn, nb):
        logging.debug("Request %d random activities" % nb)

        conn[CONNECTION_INTERFACE_REQUESTS].CreateChannel(
            { 'org.freedesktop.Telepathy.Channel.ChannelType':
                'org.laptop.Telepathy.Channel.Type.ActivityView',
               'org.laptop.Telepathy.Channel.Interface.View.MaxSize': nb
          })

    def __publish_gadget_changed_cb(self, client_, cnxn_id_, entry, user_data=None):
        if entry.value.type == gconf.VALUE_BOOL:
            publish = entry.value.get_bool()

            for conn in self._conn_watcher.get_connections():
                if CONN_INTERFACE_GADGET not in conn:
                    continue

                gadget_discovered = conn[PROPERTIES_IFACE].Get(CONN_INTERFACE_GADGET,
                    'GadgetAvailable')
                if gadget_discovered:
                    logging.debug("publish_gadget gconf key changed."
                            " Publish our status: %r" %
                            (conn.service_name.split('.')[-1], publish))
                    conn[CONN_INTERFACE_GADGET].Publish(publish)

    def _get_buddies_cb(self, buddy_list):
        for buddy in buddy_list:
            self._buddy_appeared_cb(self._pservice, buddy)

    def _get_activities_cb(self, activity_list):
        for act in activity_list:
            self._check_activity(act)

    def get_activities(self):
        return self._activities.values()

    def get_buddies(self):
        return self._buddies.values()

    def _buddy_activity_changed_cb(self, model, cur_activity):
        if not self._buddies.has_key(model.get_buddy().object_path()):
            return
        if cur_activity and self._activities.has_key(cur_activity.props.id):
            activity_model = self._activities[cur_activity.props.id]
            self.emit('buddy-moved', model, activity_model)
        else:
            self.emit('buddy-moved', model, None)

    def _buddy_appeared_cb(self, pservice, buddy):
        if self._buddies.has_key(buddy.object_path()):
            return

        model = BuddyModel(buddy=buddy)
        model.connect('current-activity-changed',
                      self._buddy_activity_changed_cb)
        self._buddies[buddy.object_path()] = model
        self.emit('buddy-added', model)

        cur_activity = buddy.props.current_activity
        if cur_activity:
            self._buddy_activity_changed_cb(model, cur_activity)

    def _buddy_disappeared_cb(self, pservice, buddy):
        if not self._buddies.has_key(buddy.object_path()):
            return
        self.emit('buddy-removed', self._buddies[buddy.object_path()])
        del self._buddies[buddy.object_path()]

    def _activity_appeared_cb(self, pservice, act):
        self._check_activity(act)

    def _check_activity(self, presence_activity):
        registry = bundleregistry.get_registry()
        bundle = registry.get_bundle(presence_activity.props.type)
        if not bundle:
            return
        if self.has_activity(presence_activity.props.id):
            return
        self.add_activity(bundle, presence_activity)

    def has_activity(self, activity_id):
        return self._activities.has_key(activity_id)

    def get_activity(self, activity_id):
        if self.has_activity(activity_id):
            return self._activities[activity_id]
        else:
            return None

    def add_activity(self, bundle, act):
        model = ActivityModel(act, bundle)
        self._activities[model.get_id()] = model
        self.emit('activity-added', model)

        for buddy in self._pservice.get_buddies():
            cur_activity = buddy.props.current_activity
            object_path = buddy.object_path()
            if cur_activity == activity and object_path in self._buddies:
                buddy_model = self._buddies[object_path]
                self.emit('buddy-moved', buddy_model, model)

    def _activity_disappeared_cb(self, pservice, act):
        if self._activities.has_key(act.props.id):
            activity_model = self._activities[act.props.id]
            self.emit('activity-removed', activity_model)
            del self._activities[act.props.id]

_model = None

def get_model():
    global _model
    if _model is None:
        _model = Neighborhood()
    return _model
