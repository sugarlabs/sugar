# Copyright (C) 2010 Collabora Ltd. <http://www.collabora.co.uk/>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
from functools import partial
from hashlib import sha1

from gi.repository import GObject
from gi.repository import Gio
import dbus
from dbus import PROPERTIES_IFACE
from telepathy.interfaces import ACCOUNT, \
    ACCOUNT_MANAGER, \
    CHANNEL, \
    CHANNEL_INTERFACE_GROUP, \
    CHANNEL_TYPE_CONTACT_LIST, \
    CHANNEL_TYPE_FILE_TRANSFER, \
    CLIENT, \
    CONNECTION, \
    CONNECTION_INTERFACE_ALIASING, \
    CONNECTION_INTERFACE_CONTACTS, \
    CONNECTION_INTERFACE_CONTACT_CAPABILITIES, \
    CONNECTION_INTERFACE_REQUESTS, \
    CONNECTION_INTERFACE_SIMPLE_PRESENCE
from telepathy.constants import HANDLE_TYPE_CONTACT, \
    HANDLE_TYPE_LIST, \
    CONNECTION_PRESENCE_TYPE_OFFLINE, \
    CONNECTION_STATUS_CONNECTED, \
    CONNECTION_STATUS_DISCONNECTED
from telepathy.client import Connection, Channel

from sugar3.graphics.xocolor import XoColor
from sugar3.profile import get_profile

from jarabe.model.buddy import BuddyModel, get_owner_instance
from jarabe.model import bundleregistry
from jarabe.model import shell


ACCOUNT_MANAGER_SERVICE = 'org.freedesktop.Telepathy.AccountManager'
ACCOUNT_MANAGER_PATH = '/org/freedesktop/Telepathy/AccountManager'
CHANNEL_DISPATCHER_SERVICE = 'org.freedesktop.Telepathy.ChannelDispatcher'
CHANNEL_DISPATCHER_PATH = '/org/freedesktop/Telepathy/ChannelDispatcher'
SUGAR_CLIENT_SERVICE = 'org.freedesktop.Telepathy.Client.Sugar'
SUGAR_CLIENT_PATH = '/org/freedesktop/Telepathy/Client/Sugar'

CONNECTION_INTERFACE_BUDDY_INFO = 'org.laptop.Telepathy.BuddyInfo'
CONNECTION_INTERFACE_ACTIVITY_PROPERTIES = \
    'org.laptop.Telepathy.ActivityProperties'

_QUERY_DBUS_TIMEOUT = 200
"""
Time in seconds to wait when querying contact properties. Some jabber servers
will be very slow in returning these queries, so just be patient.
"""

_model = None


class ActivityModel(GObject.GObject):
    __gsignals__ = {
        'current-buddy-added': (GObject.SignalFlags.RUN_FIRST, None,
                                ([object])),
        'current-buddy-removed': (GObject.SignalFlags.RUN_FIRST, None,
                                  ([object])),
        'buddy-added': (GObject.SignalFlags.RUN_FIRST, None,
                        ([object])),
        'buddy-removed': (GObject.SignalFlags.RUN_FIRST, None,
                          ([object])),
    }

    def __init__(self, activity_id, room_handle):
        GObject.GObject.__init__(self)

        self.activity_id = activity_id
        self.room_handle = room_handle
        self._bundle = None
        self._color = None
        self._private = True
        self._name = None
        self._current_buddies = []
        self._buddies = []

    def get_color(self):
        return self._color

    def set_color(self, color):
        self._color = color

    color = GObject.property(type=object, getter=get_color, setter=set_color)

    def get_bundle(self):
        return self._bundle

    def set_bundle(self, bundle):
        self._bundle = bundle

    bundle = GObject.property(type=object, getter=get_bundle,
                              setter=set_bundle)

    def get_name(self):
        return self._name

    def set_name(self, name):
        self._name = name

    name = GObject.property(type=object, getter=get_name, setter=set_name)

    def is_private(self):
        return self._private

    def set_private(self, private):
        self._private = private

    private = GObject.property(type=object, getter=is_private,
                               setter=set_private)

    def get_buddies(self):
        return self._buddies

    def add_buddy(self, buddy):
        self._buddies.append(buddy)
        self.notify('buddies')
        self.emit('buddy-added', buddy)

    def remove_buddy(self, buddy):
        self._buddies.remove(buddy)
        self.notify('buddies')
        self.emit('buddy-removed', buddy)

    buddies = GObject.property(type=object, getter=get_buddies)

    def get_current_buddies(self):
        return self._current_buddies

    def add_current_buddy(self, buddy):
        self._current_buddies.append(buddy)
        self.notify('current-buddies')
        self.emit('current-buddy-added', buddy)

    def remove_current_buddy(self, buddy):
        self._current_buddies.remove(buddy)
        self.notify('current-buddies')
        self.emit('current-buddy-removed', buddy)

    current_buddies = GObject.property(type=object, getter=get_current_buddies)


class _Account(GObject.GObject):
    __gsignals__ = {
        'activity-added': (GObject.SignalFlags.RUN_FIRST, None,
                           ([object, object])),
        'activity-updated': (GObject.SignalFlags.RUN_FIRST, None,
                             ([object, object])),
        'activity-removed': (GObject.SignalFlags.RUN_FIRST, None,
                             ([object])),
        'buddy-added': (GObject.SignalFlags.RUN_FIRST, None,
                        ([object, object, object])),
        'buddy-updated': (GObject.SignalFlags.RUN_FIRST, None,
                          ([object, object])),
        'buddy-removed': (GObject.SignalFlags.RUN_FIRST, None,
                          ([object])),
        'buddy-joined-activity': (GObject.SignalFlags.RUN_FIRST, None,
                                  ([object, object])),
        'buddy-left-activity': (GObject.SignalFlags.RUN_FIRST, None,
                                ([object, object])),
        'current-activity-updated': (GObject.SignalFlags.RUN_FIRST,
                                     None, ([object, object])),
        'connected': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'disconnected': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, account_path):
        GObject.GObject.__init__(self)

        self.object_path = account_path

        self._connection = None
        self._buddy_handles = {}
        self._activity_handles = {}
        self._self_handle = None

        self._buddies_per_activity = {}
        self._activities_per_buddy = {}

        self._home_changed_hid = None

        self._start_listening()

    def _close_connection(self):
        self._connection = None
        if self._home_changed_hid is not None:
            model = shell.get_model()
            model.disconnect(self._home_changed_hid)
            self._home_changed_hid = None

    def _start_listening(self):
        bus = dbus.Bus()
        obj = bus.get_object(ACCOUNT_MANAGER_SERVICE, self.object_path)
        obj.Get(ACCOUNT, 'Connection',
                reply_handler=self.__got_connection_cb,
                error_handler=partial(self.__error_handler_cb,
                                      'Account.GetConnection'))
        obj.connect_to_signal(
            'AccountPropertyChanged', self.__account_property_changed_cb)

    def __error_handler_cb(self, function_name, error):
        raise RuntimeError('Error when calling %s: %s' % (function_name,
                                                          error))

    def __got_connection_cb(self, connection_path):
        logging.debug('_Account.__got_connection_cb %r', connection_path)

        if connection_path == '/':
            self._check_registration_error()
            return

        self._prepare_connection(connection_path)

    def _check_registration_error(self):
        """
        See if a previous connection attempt failed and we need to unset
        the register flag.
        """
        bus = dbus.Bus()
        obj = bus.get_object(ACCOUNT_MANAGER_SERVICE, self.object_path)
        obj.Get(ACCOUNT, 'ConnectionError',
                reply_handler=self.__got_connection_error_cb,
                error_handler=partial(self.__error_handler_cb,
                                      'Account.GetConnectionError'))

    def __got_connection_error_cb(self, error):
        logging.debug('_Account.__got_connection_error_cb %r', error)
        if error == 'org.freedesktop.Telepathy.Error.RegistrationExists':
            bus = dbus.Bus()
            obj = bus.get_object(ACCOUNT_MANAGER_SERVICE, self.object_path)
            obj.UpdateParameters({'register': False}, [],
                                 dbus_interface=ACCOUNT)

    def __account_property_changed_cb(self, properties):
        logging.debug('_Account.__account_property_changed_cb %r %r %r',
                      self.object_path, properties.get('Connection', None),
                      self._connection)
        if 'Connection' not in properties:
            return
        if properties['Connection'] == '/':
            self._check_registration_error()
            self._close_connection()
        elif self._connection is None:
            self._prepare_connection(properties['Connection'])

    def _prepare_connection(self, connection_path):
        connection_name = connection_path.replace('/', '.')[1:]

        self._connection = Connection(connection_name, connection_path,
                                      ready_handler=self.__connection_ready_cb)

    def __connection_ready_cb(self, connection):
        logging.debug('_Account.__connection_ready_cb %r',
                      connection.object_path)
        connection.connect_to_signal('StatusChanged',
                                     self.__status_changed_cb)

        connection[PROPERTIES_IFACE].Get(CONNECTION,
                                         'Status',
                                         reply_handler=self.__get_status_cb,
                                         error_handler=partial(
                                             self.__error_handler_cb,
                                             'Connection.GetStatus'))

    def __get_status_cb(self, status):
        logging.debug('_Account.__get_status_cb %r %r',
                      self._connection.object_path, status)
        self._update_status(status)

    def __status_changed_cb(self, status, reason):
        logging.debug('_Account.__status_changed_cb %r %r', status, reason)
        self._update_status(status)

    def _update_status(self, status):
        if status == CONNECTION_STATUS_CONNECTED:
            self._connection[PROPERTIES_IFACE].Get(
                CONNECTION,
                'SelfHandle',
                reply_handler=self.__get_self_handle_cb,
                error_handler=partial(
                    self.__error_handler_cb,
                    'Connection.GetSelfHandle'))
            self.emit('connected')
        else:
            for contact_handle, contact_id in self._buddy_handles.items():
                if contact_id is not None:
                    self.emit('buddy-removed', contact_id)

            for room_handle, activity_id in self._activity_handles.items():
                self.emit('activity-removed', activity_id)

            self._buddy_handles = {}
            self._activity_handles = {}
            self._buddies_per_activity = {}
            self._activities_per_buddy = {}

            self.emit('disconnected')

        if status == CONNECTION_STATUS_DISCONNECTED:
            self._close_connection()

    def __get_self_handle_cb(self, self_handle):
        self._self_handle = self_handle

        if CONNECTION_INTERFACE_CONTACT_CAPABILITIES in self._connection:
            interface = CONNECTION_INTERFACE_CONTACT_CAPABILITIES
            connection = self._connection[interface]
            client_name = CLIENT + '.Sugar.FileTransfer'
            file_transfer_channel_class = {
                CHANNEL + '.ChannelType': CHANNEL_TYPE_FILE_TRANSFER,
                CHANNEL + '.TargetHandleType': HANDLE_TYPE_CONTACT}
            capabilities = []
            connection.UpdateCapabilities(
                [(client_name, [file_transfer_channel_class], capabilities)],
                reply_handler=self.__update_capabilities_cb,
                error_handler=partial(self.__error_handler_cb,
                                      'Connection.UpdateCapabilities'))

        connection = self._connection[CONNECTION_INTERFACE_ALIASING]
        connection.connect_to_signal('AliasesChanged',
                                     self.__aliases_changed_cb)

        connection = self._connection[CONNECTION_INTERFACE_SIMPLE_PRESENCE]
        connection.connect_to_signal('PresencesChanged',
                                     self.__presences_changed_cb)

        if CONNECTION_INTERFACE_BUDDY_INFO in self._connection:
            connection = self._connection[CONNECTION_INTERFACE_BUDDY_INFO]
            connection.connect_to_signal('PropertiesChanged',
                                         self.__buddy_info_updated_cb,
                                         byte_arrays=True)

            connection.connect_to_signal('ActivitiesChanged',
                                         self.__buddy_activities_changed_cb)

            connection.connect_to_signal('CurrentActivityChanged',
                                         self.__current_activity_changed_cb)

            if self._home_changed_hid is None:
                home_model = shell.get_model()
                self._home_changed_hid = home_model.connect(
                    'active-activity-changed',
                    self.__active_activity_changed_cb)
        else:
            logging.warning('Connection %s does not support OLPC buddy '
                            'properties', self._connection.object_path)

        if CONNECTION_INTERFACE_ACTIVITY_PROPERTIES in self._connection:
            connection = self._connection[
                CONNECTION_INTERFACE_ACTIVITY_PROPERTIES]
            connection.connect_to_signal(
                'ActivityPropertiesChanged',
                self.__activity_properties_changed_cb)
        else:
            logging.warning('Connection %s does not support OLPC activity '
                            'properties', self._connection.object_path)

        properties = {
            CHANNEL + '.ChannelType': CHANNEL_TYPE_CONTACT_LIST,
            CHANNEL + '.TargetHandleType': HANDLE_TYPE_LIST,
            CHANNEL + '.TargetID': 'subscribe',
        }
        properties = dbus.Dictionary(properties, signature='sv')
        connection = self._connection[CONNECTION_INTERFACE_REQUESTS]
        is_ours, channel_path, properties = \
            connection.EnsureChannel(properties)

        channel = Channel(self._connection.service_name, channel_path)
        channel[CHANNEL_INTERFACE_GROUP].connect_to_signal(
            'MembersChanged', self.__members_changed_cb)

        channel[PROPERTIES_IFACE].Get(
            CHANNEL_INTERFACE_GROUP,
            'Members',
            reply_handler=self.__get_members_ready_cb,
            error_handler=partial(
                self.__error_handler_cb,
                'Connection.GetMembers'))

    def __active_activity_changed_cb(self, model, home_activity):
        if home_activity is None:
            return

        room_handle = 0
        home_activity_id = home_activity.get_activity_id()
        for handle, activity_id in self._activity_handles.items():
            if home_activity_id == activity_id:
                room_handle = handle
                break
        if room_handle == 0:
            home_activity_id = ''

        connection = self._connection[CONNECTION_INTERFACE_BUDDY_INFO]
        connection.SetCurrentActivity(
            home_activity_id,
            room_handle,
            reply_handler=self.__set_current_activity_cb,
            error_handler=self.__set_current_activity_error_cb)

    def __set_current_activity_cb(self):
        logging.debug('_Account.__set_current_activity_cb')

    def __set_current_activity_error_cb(self, error):
        logging.debug('_Account.__set_current_activity__error_cb %r', error)

    def __update_capabilities_cb(self):
        pass

    def __aliases_changed_cb(self, aliases):
        logging.debug('_Account.__aliases_changed_cb')
        for handle, alias in aliases:
            if handle in self._buddy_handles:
                logging.debug('Got handle %r with nick %r, going to update',
                              handle, alias)
                properties = {CONNECTION_INTERFACE_ALIASING + '/alias': alias}
                self.emit('buddy-updated', self._buddy_handles[handle],
                          properties)

    def __presences_changed_cb(self, presences):
        logging.debug('_Account.__presences_changed_cb %r', presences)
        for handle, presence in presences.iteritems():
            if handle in self._buddy_handles:
                presence_type, status_, message_ = presence
                if presence_type == CONNECTION_PRESENCE_TYPE_OFFLINE:
                    contact_id = self._buddy_handles[handle]
                    del self._buddy_handles[handle]
                    self.emit('buddy-removed', contact_id)

    def __buddy_info_updated_cb(self, handle, properties):
        logging.debug('_Account.__buddy_info_updated_cb %r', handle)
        if handle in self._buddy_handles:
            self.emit('buddy-updated', self._buddy_handles[handle], properties)

    def __current_activity_changed_cb(self, contact_handle, activity_id,
                                      room_handle):
        logging.debug('_Account.__current_activity_changed_cb %r %r %r',
                      contact_handle, activity_id, room_handle)
        if contact_handle in self._buddy_handles:
            contact_id = self._buddy_handles[contact_handle]
            if not activity_id and room_handle:
                activity_id = self._activity_handles.get(room_handle, '')
            self.emit('current-activity-updated', contact_id, activity_id)

    def __get_current_activity_cb(self, contact_handle, activity_id,
                                  room_handle):
        logging.debug('_Account.__get_current_activity_cb %r %r %r',
                      contact_handle, activity_id, room_handle)

        if contact_handle in self._buddy_handles:
            contact_id = self._buddy_handles[contact_handle]
            if not activity_id and room_handle:
                activity_id = self._activity_handles.get(room_handle, '')
            self.emit('current-activity-updated', contact_id, activity_id)

    def __buddy_activities_changed_cb(self, buddy_handle, activities):
        self._update_buddy_activities(buddy_handle, activities)

    def _update_buddy_activities(self, buddy_handle, activities):
        logging.debug('_Account._update_buddy_activities')

        if buddy_handle not in self._activities_per_buddy:
            self._activities_per_buddy[buddy_handle] = set()

        for activity_id, room_handle in activities:
            if room_handle not in self._activity_handles:
                self._activity_handles[room_handle] = activity_id

                if buddy_handle == self._self_handle:
                    home_model = shell.get_model()
                    activity = home_model.get_active_activity()
                    if activity.get_activity_id() == activity_id:
                        connection = self._connection[
                            CONNECTION_INTERFACE_BUDDY_INFO]
                        connection.SetCurrentActivity(
                            activity_id,
                            room_handle,
                            reply_handler=self.__set_current_activity_cb,
                            error_handler=self.__set_current_activity_error_cb)

                self.emit('activity-added', room_handle, activity_id)

                connection = self._connection[
                    CONNECTION_INTERFACE_ACTIVITY_PROPERTIES]
                connection.GetProperties(
                    room_handle,
                    reply_handler=partial(self.__get_properties_cb,
                                          room_handle),
                    error_handler=partial(self.__error_handler_cb,
                                          'ActivityProperties.GetProperties'))

                if buddy_handle != self._self_handle:
                    # Sometimes we'll get CurrentActivityChanged before we get
                    # to know about the activity so we miss the event. In that
                    # case, request again the current activity for this buddy.
                    connection = self._connection[
                        CONNECTION_INTERFACE_BUDDY_INFO]
                    connection.GetCurrentActivity(
                        buddy_handle,
                        reply_handler=partial(self.__get_current_activity_cb,
                                              buddy_handle),
                        error_handler=partial(self.__error_handler_cb,
                                              'BuddyInfo.GetCurrentActivity'))

            if activity_id not in self._buddies_per_activity:
                self._buddies_per_activity[activity_id] = set()
            self._buddies_per_activity[activity_id].add(buddy_handle)
            if activity_id not in self._activities_per_buddy[buddy_handle]:
                self._activities_per_buddy[buddy_handle].add(activity_id)
                if buddy_handle != self._self_handle:
                    self.emit('buddy-joined-activity',
                              self._buddy_handles[buddy_handle],
                              activity_id)

        current_activity_ids = \
            [activity_id for activity_id, room_handle in activities]
        for activity_id in self._activities_per_buddy[buddy_handle].copy():
            if activity_id not in current_activity_ids:
                self._remove_buddy_from_activity(buddy_handle, activity_id)

    def __get_properties_cb(self, room_handle, properties):
        logging.debug('_Account.__get_properties_cb %r %r', room_handle,
                      properties)
        if properties:
            self._update_activity(room_handle, properties)

    def _remove_buddy_from_activity(self, buddy_handle, activity_id):
        if buddy_handle in self._buddies_per_activity[activity_id]:
            self._buddies_per_activity[activity_id].remove(buddy_handle)

        if activity_id in self._activities_per_buddy[buddy_handle]:
            self._activities_per_buddy[buddy_handle].remove(activity_id)

        if buddy_handle != self._self_handle:
            self.emit('buddy-left-activity',
                      self._buddy_handles[buddy_handle],
                      activity_id)

        if not self._buddies_per_activity[activity_id]:
            del self._buddies_per_activity[activity_id]

            for room_handle in self._activity_handles.copy():
                if self._activity_handles[room_handle] == activity_id:
                    del self._activity_handles[room_handle]
                    break

            self.emit('activity-removed', activity_id)

    def __activity_properties_changed_cb(self, room_handle, properties):
        logging.debug('_Account.__activity_properties_changed_cb %r %r',
                      room_handle, properties)
        self._update_activity(room_handle, properties)

    def _update_activity(self, room_handle, properties):
        if room_handle in self._activity_handles:
            self.emit('activity-updated', self._activity_handles[room_handle],
                      properties)
        else:
            logging.debug('_Account.__activity_properties_changed_cb unknown '
                          'activity')
            # We don't get ActivitiesChanged for the owner of the connection,
            # so we query for its activities in order to find out.
            if CONNECTION_INTERFACE_BUDDY_INFO in self._connection:
                handle = self._self_handle
                connection = self._connection[CONNECTION_INTERFACE_BUDDY_INFO]
                connection.GetActivities(
                    handle,
                    reply_handler=partial(self.__got_activities_cb, handle),
                    error_handler=partial(self.__error_handler_cb,
                                          'BuddyInfo.Getactivities'))

    def __members_changed_cb(self, message, added, removed, local_pending,
                             remote_pending, actor, reason):
        self._add_buddy_handles(added)

    def __get_members_ready_cb(self, handles):
        logging.debug('_Account.__get_members_ready_cb %r', handles)
        if not handles:
            return

        self._add_buddy_handles(handles)

    def _add_buddy_handles(self, handles):
        logging.debug('_Account._add_buddy_handles %r', handles)
        interfaces = [CONNECTION, CONNECTION_INTERFACE_ALIASING]
        self._connection[CONNECTION_INTERFACE_CONTACTS].GetContactAttributes(
            handles, interfaces, False,
            reply_handler=self.__get_contact_attributes_cb,
            error_handler=partial(self.__error_handler_cb,
                                  'Contacts.GetContactAttributes'))

    def __got_buddy_info_cb(self, handle, nick, properties):
        logging.debug('_Account.__got_buddy_info_cb %r', handle)
        self.emit('buddy-updated', self._buddy_handles[handle], properties)

    def __get_contact_attributes_cb(self, attributes):
        logging.debug('_Account.__get_contact_attributes_cb %r',
                      attributes.keys())

        for handle in attributes.keys():
            nick = attributes[handle][CONNECTION_INTERFACE_ALIASING + '/alias']

            if handle == self._self_handle:
                logging.debug('_Account.__get_contact_attributes_cb,'
                              ' do not add ourself %r', handle)
                continue

            if handle in self._buddy_handles and \
                    not self._buddy_handles[handle] is None:
                logging.debug('Got handle %r with nick %r, going to update',
                              handle, nick)
                self.emit('buddy-updated', self._buddy_handles[handle],
                          attributes[handle])
            else:
                logging.debug('Got handle %r with nick %r, going to add',
                              handle, nick)

                contact_id = attributes[handle][CONNECTION + '/contact-id']
                self._buddy_handles[handle] = contact_id

                if CONNECTION_INTERFACE_BUDDY_INFO in self._connection:
                    connection = \
                        self._connection[CONNECTION_INTERFACE_BUDDY_INFO]

                    connection.GetProperties(
                        handle,
                        reply_handler=partial(self.__got_buddy_info_cb, handle,
                                              nick),
                        error_handler=partial(self.__error_handler_cb,
                                              'BuddyInfo.GetProperties'),
                        byte_arrays=True,
                        timeout=_QUERY_DBUS_TIMEOUT)

                    connection.GetActivities(
                        handle,
                        reply_handler=partial(self.__got_activities_cb,
                                              handle),
                        error_handler=partial(self.__error_handler_cb,
                                              'BuddyInfo.GetActivities'),
                        timeout=_QUERY_DBUS_TIMEOUT)

                    connection.GetCurrentActivity(
                        handle,
                        reply_handler=partial(self.__get_current_activity_cb,
                                              handle),
                        error_handler=partial(self.__error_handler_cb,
                                              'BuddyInfo.GetCurrentActivity'),
                        timeout=_QUERY_DBUS_TIMEOUT)

                self.emit('buddy-added', contact_id, nick, handle)

    def __got_activities_cb(self, buddy_handle, activities):
        logging.debug('_Account.__got_activities_cb %r %r', buddy_handle,
                      activities)
        self._update_buddy_activities(buddy_handle, activities)

    def enable(self):
        logging.debug('_Account.enable %s', self.object_path)
        self._set_enabled(True)

    def disable(self):
        logging.debug('_Account.disable %s', self.object_path)
        self._set_enabled(False)
        self._close_connection()

    def _set_enabled(self, value):
        bus = dbus.Bus()
        obj = bus.get_object(ACCOUNT_MANAGER_SERVICE, self.object_path)
        obj.Set(ACCOUNT, 'Enabled', value,
                reply_handler=self.__set_enabled_cb,
                error_handler=partial(self.__error_handler_cb,
                                      'Account.SetEnabled'),
                dbus_interface=dbus.PROPERTIES_IFACE)

    def __set_enabled_cb(self):
        logging.debug('_Account.__set_enabled_cb success')


class Neighborhood(GObject.GObject):
    __gsignals__ = {
        'activity-added': (GObject.SignalFlags.RUN_FIRST, None,
                           ([object])),
        'activity-removed': (GObject.SignalFlags.RUN_FIRST, None,
                             ([object])),
        'buddy-added': (GObject.SignalFlags.RUN_FIRST, None,
                        ([object])),
        'buddy-removed': (GObject.SignalFlags.RUN_FIRST, None,
                          ([object])),
    }

    def __init__(self):
        GObject.GObject.__init__(self)

        self._buddies = {None: get_owner_instance()}
        self._activities = {}
        self._link_local_account = None
        self._server_account = None
        self._shell_model = shell.get_model()

        self._settings_collaboration = \
            Gio.Settings('org.sugarlabs.collaboration')
        self._settings_collaboration.connect(
            'changed::jabber-server', self.__jabber_server_changed_cb)
        self._settings_user = Gio.Settings('org.sugarlabs.user')
        self._settings_user.connect(
            'changed::nick', self.__nick_changed_cb)

        bus = dbus.Bus()
        obj = bus.get_object(ACCOUNT_MANAGER_SERVICE, ACCOUNT_MANAGER_PATH)
        account_manager = dbus.Interface(obj, ACCOUNT_MANAGER)
        account_manager.Get(ACCOUNT_MANAGER, 'ValidAccounts',
                            dbus_interface=PROPERTIES_IFACE,
                            reply_handler=self.__got_accounts_cb,
                            error_handler=self.__error_handler_cb)

    def __got_accounts_cb(self, account_paths):
        self._link_local_account = \
            self._ensure_link_local_account(account_paths)
        self._connect_to_account(self._link_local_account)

        self._server_account = self._ensure_server_account(account_paths)
        self._connect_to_account(self._server_account)

    def __error_handler_cb(self, error):
        raise RuntimeError(error)

    def _connect_to_account(self, account):
        account.connect('buddy-added', self.__buddy_added_cb)
        account.connect('buddy-updated', self.__buddy_updated_cb)
        account.connect('buddy-removed', self.__buddy_removed_cb)
        account.connect('buddy-joined-activity',
                        self.__buddy_joined_activity_cb)
        account.connect('buddy-left-activity', self.__buddy_left_activity_cb)
        account.connect('activity-added', self.__activity_added_cb)
        account.connect('activity-updated', self.__activity_updated_cb)
        account.connect('activity-removed', self.__activity_removed_cb)
        account.connect('current-activity-updated',
                        self.__current_activity_updated_cb)
        account.connect('connected', self.__account_connected_cb)
        account.connect('disconnected', self.__account_disconnected_cb)

    def __account_connected_cb(self, account):
        logging.debug('__account_connected_cb %s', account.object_path)
        if account == self._server_account:
            self._link_local_account.disable()

    def __account_disconnected_cb(self, account):
        logging.debug('__account_disconnected_cb %s', account.object_path)
        if account == self._server_account:
            self._link_local_account.enable()

    def _get_published_name(self):
        """Construct the published name based on the public key

        Limit the name to be only 8 characters maximum. The avahi
        service name has a 64 character limit. It consists of
        the room name, the published name and the host name.

        """
        public_key_hash = sha1(get_profile().pubkey).hexdigest()
        return public_key_hash[:8]

    def _ensure_link_local_account(self, account_paths):
        for account_path in account_paths:
            if 'salut' in account_path:
                logging.debug('Already have a Salut account')
                account = _Account(account_path)
                account.enable()
                return account

        logging.debug('Still dont have a Salut account, creating one')

        nick = self._settings_user.get_string('nick')

        params = {
            'nickname': nick,
            'first-name': '',
            'last-name': '',
            'jid': self._get_jabber_account_id(),
            'published-name': self._get_published_name(),
        }

        properties = {
            ACCOUNT + '.Enabled': True,
            ACCOUNT + '.Nickname': nick,
            ACCOUNT + '.ConnectAutomatically': True,
        }

        bus = dbus.Bus()
        obj = bus.get_object(ACCOUNT_MANAGER_SERVICE, ACCOUNT_MANAGER_PATH)
        account_manager = dbus.Interface(obj, ACCOUNT_MANAGER)
        account_path = account_manager.CreateAccount('salut', 'local-xmpp',
                                                     'salut', params,
                                                     properties)
        return _Account(account_path)

    def _ensure_server_account(self, account_paths):
        for account_path in account_paths:
            if 'gabble' in account_path:
                logging.debug('Already have a Gabble account')
                account = _Account(account_path)
                account.enable()
                return account

        logging.debug('Still dont have a Gabble account, creating one')

        nick = self._settings_user.get_string('nick')
        server = self._settings_collaboration.get_string('jabber-server')
        key_hash = get_profile().privkey_hash

        params = {
            'account': self._get_jabber_account_id(),
            'password': key_hash,
            'server': server,
            'resource': 'sugar',
            'require-encryption': True,
            'ignore-ssl-errors': True,
            'register': True,
            'old-ssl': True,
            'port': dbus.UInt32(5223),
        }

        properties = {
            ACCOUNT + '.Enabled': True,
            ACCOUNT + '.Nickname': nick,
            ACCOUNT + '.ConnectAutomatically': True,
        }

        bus = dbus.Bus()
        obj = bus.get_object(ACCOUNT_MANAGER_SERVICE, ACCOUNT_MANAGER_PATH)
        account_manager = dbus.Interface(obj, ACCOUNT_MANAGER)
        account_path = account_manager.CreateAccount('gabble', 'jabber',
                                                     'jabber', params,
                                                     properties)
        return _Account(account_path)

    def _get_jabber_account_id(self):
        public_key_hash = sha1(get_profile().pubkey).hexdigest()
        server = self._settings_collaboration.get_string('jabber-server')
        return '%s@%s' % (public_key_hash, server)

    def __jabber_server_changed_cb(self, settings, key):
        logging.debug('__jabber_server_changed_cb')

        bus = dbus.Bus()
        account = bus.get_object(ACCOUNT_MANAGER_SERVICE,
                                 self._server_account.object_path)

        server = settings.get_string('jabber-server')
        account_id = self._get_jabber_account_id()
        params_needing_reconnect = account.UpdateParameters(
            {'server': server,
             'account': account_id,
             'register': True},
            dbus.Array([], 's'), dbus_interface=ACCOUNT)
        if params_needing_reconnect:
            account.Reconnect()

        self._update_jid()

    def __nick_changed_cb(self, settings, key):
        logging.debug('__nick_changed_cb')

        nick = settings.get_string('nick')

        bus = dbus.Bus()
        server_obj = bus.get_object(ACCOUNT_MANAGER_SERVICE,
                                    self._server_account.object_path)
        server_obj.Set(ACCOUNT, 'Nickname', nick,
                       dbus_interface=PROPERTIES_IFACE)

        link_local_obj = bus.get_object(ACCOUNT_MANAGER_SERVICE,
                                        self._link_local_account.object_path)
        link_local_obj.Set(ACCOUNT, 'Nickname', nick,
                           dbus_interface=PROPERTIES_IFACE)
        params_needing_reconnect = link_local_obj.UpdateParameters(
            {'nickname': nick, 'published-name': self._get_published_name()},
            dbus.Array([], 's'), dbus_interface=ACCOUNT)
        if params_needing_reconnect:
            link_local_obj.Reconnect()

        self._update_jid()

    def _update_jid(self):
        bus = dbus.Bus()
        account = bus.get_object(ACCOUNT_MANAGER_SERVICE,
                                 self._link_local_account.object_path)

        account_id = self._get_jabber_account_id()
        params_needing_reconnect = account.UpdateParameters(
            {'jid': account_id}, dbus.Array([], 's'), dbus_interface=ACCOUNT)
        if params_needing_reconnect:
            account.Reconnect()

    def __buddy_added_cb(self, account, contact_id, nick, handle):
        logging.debug('__buddy_added_cb %r', contact_id)

        if contact_id in self._buddies:
            logging.debug('__buddy_added_cb buddy already tracked')
            return

        buddy = BuddyModel(
            nick=nick,
            account=account.object_path,
            contact_id=contact_id,
            handle=handle)
        self._buddies[contact_id] = buddy

    def __buddy_updated_cb(self, account, contact_id, properties):
        logging.debug('__buddy_updated_cb %r', contact_id)
        if contact_id is None:
            # Don't know the contact-id yet, will get the full state later
            return

        if contact_id not in self._buddies:
            logging.debug('__buddy_updated_cb Unknown buddy with contact_id'
                          ' %r', contact_id)
            return

        buddy = self._buddies[contact_id]

        is_new = buddy.props.key is None and 'key' in properties

        if 'color' in properties:
            # arrives unicode but we connect with byte_arrays=True - SL #4157
            buddy.props.color = XoColor(str(properties['color']))

        if 'key' in properties:
            buddy.props.key = properties['key']

        nick_key = CONNECTION_INTERFACE_ALIASING + '/alias'
        if nick_key in properties:
            buddy.props.nick = properties[nick_key]

        if is_new:
            self.emit('buddy-added', buddy)

    def __buddy_removed_cb(self, account, contact_id):
        logging.debug('Neighborhood.__buddy_removed_cb %r', contact_id)
        if contact_id not in self._buddies:
            logging.debug('Neighborhood.__buddy_removed_cb Unknown buddy with '
                          'contact_id %r', contact_id)
            return

        buddy = self._buddies[contact_id]
        del self._buddies[contact_id]

        if buddy.props.key is not None:
            self.emit('buddy-removed', buddy)

    def __activity_added_cb(self, account, room_handle, activity_id):
        logging.debug('__activity_added_cb %r %r', room_handle, activity_id)
        if activity_id in self._activities:
            logging.debug('__activity_added_cb activity already tracked')
            return

        activity = ActivityModel(activity_id, room_handle)
        self._activities[activity_id] = activity

    def __activity_updated_cb(self, account, activity_id, properties):
        logging.debug('__activity_updated_cb %r %r', activity_id, properties)
        if activity_id not in self._activities:
            logging.debug('__activity_updated_cb Unknown activity with '
                          'activity_id %r', activity_id)
            return

        registry = bundleregistry.get_registry()
        bundle = registry.get_bundle(properties['type'])
        if not bundle:
            logging.warning('Ignoring shared activity we don''t have')
            return

        activity = self._activities[activity_id]

        is_new = activity.props.bundle is None

        # arrives unicode but we connect with byte_arrays=True - SL #4157
        activity.props.color = XoColor(str(properties['color']))
        activity.props.bundle = bundle
        activity.props.name = properties['name']
        activity.props.private = properties['private']

        if is_new:
            self._shell_model.add_shared_activity(activity_id,
                                                  activity.props.color)
            self.emit('activity-added', activity)

    def __activity_removed_cb(self, account, activity_id):
        logging.debug('__activity_removed_cb %r', activity_id)
        if activity_id not in self._activities:
            logging.debug('Unknown activity with id %s. Already removed?',
                          activity_id)
            return
        activity = self._activities[activity_id]
        del self._activities[activity_id]
        self._shell_model.remove_shared_activity(activity_id)

        if activity.props.bundle is not None:
            self.emit('activity-removed', activity)

    def __current_activity_updated_cb(self, account, contact_id, activity_id):
        logging.debug('__current_activity_updated_cb %r %r', contact_id,
                      activity_id)
        if contact_id not in self._buddies:
            logging.debug('__current_activity_updated_cb Unknown buddy with '
                          'contact_id %r', contact_id)
            return
        if activity_id and activity_id not in self._activities:
            logging.debug('__current_activity_updated_cb Unknown activity with'
                          ' id %s', activity_id)
            activity_id = ''

        buddy = self._buddies[contact_id]
        if buddy.props.current_activity is not None:
            if buddy.props.current_activity.activity_id == activity_id:
                return
            buddy.props.current_activity.remove_current_buddy(buddy)

        if activity_id:
            activity = self._activities[activity_id]
            buddy.props.current_activity = activity
            activity.add_current_buddy(buddy)
        else:
            buddy.props.current_activity = None

    def __buddy_joined_activity_cb(self, account, contact_id, activity_id):
        if contact_id not in self._buddies:
            logging.debug('__buddy_joined_activity_cb Unknown buddy with '
                          'contact_id %r', contact_id)
            return

        if activity_id not in self._activities:
            logging.debug('__buddy_joined_activity_cb Unknown activity with '
                          'activity_id %r', activity_id)
            return

        self._activities[activity_id].add_buddy(self._buddies[contact_id])

    def __buddy_left_activity_cb(self, account, contact_id, activity_id):
        if contact_id not in self._buddies:
            logging.debug('__buddy_left_activity_cb Unknown buddy with '
                          'contact_id %r', contact_id)
            return

        if activity_id not in self._activities:
            logging.debug('__buddy_left_activity_cb Unknown activity with '
                          'activity_id %r', activity_id)
            return

        self._activities[activity_id].remove_buddy(self._buddies[contact_id])

    def get_buddies(self):
        return self._buddies.values()

    def get_buddy_by_key(self, key):
        for buddy in self._buddies.values():
            if buddy.key == key:
                return buddy
        return None

    def get_buddy_by_handle(self, contact_handle):
        for buddy in self._buddies.values():
            if not buddy.is_owner() and buddy.handle == contact_handle:
                return buddy
        return None

    def get_activity(self, activity_id):
        return self._activities.get(activity_id, None)

    def get_activity_by_room(self, room_handle):
        for activity in self._activities.values():
            if activity.room_handle == room_handle:
                return activity
        return None

    def get_activities(self):
        return self._activities.values()


def get_model():
    global _model
    if _model is None:
        _model = Neighborhood()
    return _model
