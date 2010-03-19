# Copyright (C) 2006-2007 Red Hat, Inc.
# Copyright (C) 2010 Collabora Ltd. <http://www.collabora.co.uk/>
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

import logging
from functools import partial

import gobject
import gconf
import dbus
from dbus import PROPERTIES_IFACE
from telepathy.interfaces import ACCOUNT_MANAGER, \
                                 CHANNEL, \
                                 CHANNEL_INTERFACE_GROUP, \
                                 CHANNEL_DISPATCHER, \
                                 CHANNEL_REQUEST, \
                                 CHANNEL_TYPE_CONTACT_LIST, \
                                 CONNECTION, \
                                 CONNECTION_INTERFACE_ALIASING, \
                                 CONNECTION_INTERFACE_CONTACTS, \
                                 CONNECTION_INTERFACE_SIMPLE_PRESENCE
from telepathy.constants import HANDLE_TYPE_LIST, \
                                CONNECTION_PRESENCE_TYPE_OFFLINE
from telepathy.client import Connection, Channel

from sugar.graphics.xocolor import XoColor
from sugar import activity

from jarabe.model.buddy import BuddyModel, OwnerBuddyModel
from jarabe.model import telepathyclient
from jarabe.model import bundleregistry

ACCOUNT_MANAGER_SERVICE = 'org.freedesktop.Telepathy.AccountManager'
ACCOUNT_MANAGER_PATH = '/org/freedesktop/Telepathy/AccountManager'
CHANNEL_DISPATCHER_SERVICE = 'org.freedesktop.Telepathy.ChannelDispatcher'
CHANNEL_DISPATCHER_PATH = '/org/freedesktop/Telepathy/ChannelDispatcher'
SUGAR_CLIENT_SERVICE = 'org.freedesktop.Telepathy.Client.Sugar'
SUGAR_CLIENT_PATH = '/org/freedesktop/Telepathy/Client/Sugar'

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
        self._buddies = {None: OwnerBuddyModel()}

        bus = dbus.Bus()

        obj = bus.get_object(ACCOUNT_MANAGER_SERVICE, ACCOUNT_MANAGER_PATH)
        account_manager = dbus.Interface(obj, ACCOUNT_MANAGER)

        accounts = account_manager.Get(ACCOUNT_MANAGER_SERVICE, 'ValidAccounts',
                                       dbus_interface=PROPERTIES_IFACE)
        logging.debug('accounts %r', accounts)

        client_handler = telepathyclient.get_instance()
        client_handler.got_channel.connect(self.__got_channel_cb)

        self._ensure_link_local_account(account_manager, accounts)
        self._ensure_server_account(account_manager, accounts)

        for account in accounts:
            obj = bus.get_object(CHANNEL_DISPATCHER_SERVICE, CHANNEL_DISPATCHER_PATH)
            channel_dispatcher = dbus.Interface(obj, CHANNEL_DISPATCHER)

            properties = {
                    CHANNEL + '.ChannelType': CHANNEL_TYPE_CONTACT_LIST,
                    CHANNEL + '.TargetHandleType': HANDLE_TYPE_LIST,
                    CHANNEL + '.TargetID': 'subscribe',
                    }
            request_path = channel_dispatcher.EnsureChannel(account, properties, 0, SUGAR_CLIENT_SERVICE)
            obj = bus.get_object(CHANNEL_DISPATCHER_SERVICE, request_path)
            request = dbus.Interface(obj, CHANNEL_REQUEST)
            request.connect_to_signal('Failed', self.__channel_request_failed_cb)
            request.connect_to_signal('Succeeded', self.__channel_request_succeeded_cb)
            request.Proceed()

            logging.debug('meec %r', request)

    def _ensure_link_local_account(self, account_manager, accounts):
        # TODO: Is this the better way to check for an account?
        for account in accounts:
            if 'salut' in account:
                return

        client = gconf.client_get_default()
        nick = client.get_string('/desktop/sugar/user/nick')

        params = {
                'nickname': nick,
                'first-name': '',
                'last-name': '',
                #'jid': '%s@%s' % ('moc', 'mac'),
                'published-name': nick,
                }

        properties = {
                'org.freedesktop.Telepathy.Account.Enabled': True,
                'org.freedesktop.Telepathy.Account.Nickname': nick,
                'org.freedesktop.Telepathy.Account.ConnectAutomatically': True,
                }

        account = account_manager.CreateAccount('salut', 'local-xmpp',
                                                'salut', params, properties)
        accounts.append(account)

    def _ensure_server_account(self, account_manager, accounts):
        # TODO: Is this the better way to check for an account?
        for account in accounts:
            if 'gabble' in account:
                return

        client = gconf.client_get_default()
        nick = client.get_string('/desktop/sugar/user/nick')

        params = {
                'account': '***',
                'password': '***',
                'server': 'talk.google.com',
                'resource': 'sugar',
                }

        properties = {
                'org.freedesktop.Telepathy.Account.Enabled': True,
                'org.freedesktop.Telepathy.Account.Nickname': nick,
                'org.freedesktop.Telepathy.Account.ConnectAutomatically': True,
                }

        account = account_manager.CreateAccount('gabble', 'jabber',
                                                'jabber', params, properties)
        accounts.append(account)

    def __got_channel_cb(self, **kwargs):
        # TODO: How hacky is this?
        connection_name = kwargs['connection'].replace('/', '.')[1:]

        channel_path = kwargs['channel'][0]
        Connection(connection_name, kwargs['connection'],
                ready_handler=partial(self.__connection_ready_cb, channel_path))

    def __connection_ready_cb(self, channel_path, connection):
        channel = Channel(connection.service_name, channel_path)
        channel[CHANNEL_INTERFACE_GROUP].connect_to_signal(
                  'MembersChanged',
                  partial(self.__members_changed_cb, connection))

        connection[CONNECTION_INTERFACE_ALIASING].connect_to_signal(
                'AliasesChanged',
                partial(self.__aliases_changed_cb, connection))

        connection[CONNECTION_INTERFACE_SIMPLE_PRESENCE].connect_to_signal(
                'PresencesChanged',
                partial(self.__presences_changed_cb, connection))

        handles = channel[PROPERTIES_IFACE].Get(CHANNEL_INTERFACE_GROUP, 'Members')
        if handles:
            self._add_handles(connection, handles)

    def __presences_changed_cb(self, connection, presences):
        logging.debug('__presences_changed_cb %r', presences)
        for handle, presence in presences.iteritems():
            if (connection.service_name, handle) in self._buddies:
                presence_type, status_, message_ = presence
                if presence_type == CONNECTION_PRESENCE_TYPE_OFFLINE:
                    buddy = self._buddies[(connection.service_name, handle)]
                    del self._buddies[(connection.service_name, handle)]
                    self.emit('buddy-removed', buddy)

    def __aliases_changed_cb(self, connection, aliases):
        logging.debug('__aliases_changed_cb')
        for handle, alias in aliases:
            if (connection.service_name, handle) in self._buddies:
                logging.debug('Got handle %r with nick %r, going to update', handle, alias)
                buddy = self._buddies[(connection.service_name, handle)]
                buddy.props.nick = alias
                buddy.props.key = (connection.service_name, handle)

    def _add_handles(self, connection, handles):
        interfaces = [CONNECTION, CONNECTION_INTERFACE_ALIASING]
        connection[CONNECTION_INTERFACE_CONTACTS].GetContactAttributes(
                handles, interfaces, False,
                reply_handler=partial(self.__get_contact_attributes_cb, connection),
                error_handler=self.__error_handler_cb)

    def __error_handler_cb(self, error):
        raise RuntimeError(error)

    def __get_contact_attributes_cb(self, connection, attributes):
        logging.debug('__get_contact_attributes_cb')

        for handle in attributes.keys():
            nick = attributes[handle][CONNECTION_INTERFACE_ALIASING + '/alias']
            if (connection.service_name, handle) in self._buddies:
                logging.debug('Got handle %r with nick %r, going to update', handle, nick)
                buddy = self._buddies[(connection.service_name, handle)]
                buddy.props.nick = nick
            else:
                logging.debug('Got handle %r with nick %r, going to add', handle, nick)
                buddy = BuddyModel(nick=nick, key=(connection.service_name, handle))
                self._buddies[(connection.service_name, handle)] = buddy
                self.emit('buddy-added', buddy)

    def __members_changed_cb(self, connection, message, added, removed,
            local_pending, remote_pending, actor, reason):
        self._add_handles(connection, added)

    def __channel_request_failed_cb(self, error, message):
        raise RuntimeError('Couldn\'t retrieve contact list: %s %s', error, message)

    def __channel_request_succeeded_cb(self):
        logging.debug('Successfully ensured a ContactList channel')

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

    def __buddy_added_cb(self, **kwargs):
        self.emit('buddy-added', kwargs['buddy'])

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
