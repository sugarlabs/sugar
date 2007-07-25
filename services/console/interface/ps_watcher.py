# Copyright (C) 2007 Collabora Ltd. <http://www.collabora.co.uk/>
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
from hashlib import sha1

import dbus
from gtk import VBox, Label, TreeView, Expander, ListStore, CellRendererText,\
                ScrolledWindow, CellRendererToggle, TextView, VPaned
from gobject import timeout_add


logger = logging.getLogger('ps_watcher')
#logging.basicConfig(filename='/tmp/ps_watcher.log')
#logging.getLogger().setLevel(1)


PS_NAME = 'org.laptop.Sugar.Presence'
PS_PATH = '/org/laptop/Sugar/Presence'
PS_IFACE = PS_NAME
ACTIVITY_IFACE = PS_IFACE + '.Activity'
BUDDY_IFACE = PS_IFACE + '.Buddy'

# keep these in sync with the calls to ListStore()
ACT_COL_PATH = 0
ACT_COL_WEIGHT = 1
ACT_COL_STRIKE = 2
ACT_COL_ID = 3
ACT_COL_COLOR = 4
ACT_COL_TYPE = 5
ACT_COL_NAME = 6
ACT_COL_CONN = 7
ACT_COL_CHANNELS = 8
ACT_COL_BUDDIES = 9
BUDDY_COL_PATH = 0
BUDDY_COL_WEIGHT = 1
BUDDY_COL_STRIKE = 2
BUDDY_COL_NICK = 3
BUDDY_COL_OWNER = 4
BUDDY_COL_COLOR = 5
BUDDY_COL_IP4 = 6
BUDDY_COL_CUR_ACT = 7
BUDDY_COL_KEY_ID = 8
BUDDY_COL_ACTIVITIES = 9
BUDDY_COL_HANDLES = 10


class ActivityWatcher(object):

    def __init__(self, ps_watcher, object_path):
        self.ps_watcher = ps_watcher
        self.bus = ps_watcher.bus
        self.proxy = self.bus.get_object(self.ps_watcher.unique_name,
                                         object_path)
        self.iface = dbus.Interface(self.proxy, ACTIVITY_IFACE)
        self.object_path = object_path
        self.appearing = True
        self.disappearing = False
        timeout_add(5000, self._finish_appearing)

        self.id = '?'
        self.color = '?'
        self.type = '?'
        self.name = '?'
        self.conn = '?'
        self.channels = None
        self.buddies = None

        self.iter = self.ps_watcher.add_activity(self)

        self.iface.GetId(reply_handler=self._on_get_id_success,
                         error_handler=self._on_get_id_failure)

        self.iface.GetColor(reply_handler=self._on_get_color_success,
                            error_handler=self._on_get_color_failure)

        self.iface.GetType(reply_handler=self._on_get_type_success,
                           error_handler=self._on_get_type_failure)

        self.iface.GetName(reply_handler=self._on_get_name_success,
                           error_handler=self._on_get_name_failure)

        self.iface.connect_to_signal('NewChannel', self._on_new_channel)
        self.iface.GetChannels(reply_handler=self._on_get_channels_success,
                               error_handler=self._on_get_channels_failure)

        self.iface.connect_to_signal('BuddyJoined', self._on_buddy_joined)
        self.iface.connect_to_signal('BuddyLeft', self._on_buddy_left)
        self.iface.GetJoinedBuddies(reply_handler=self._on_get_buddies_success,
                                    error_handler=self._on_get_buddies_failure)

    def _on_buddy_joined(self, buddy):
        if self.buddies is None:
            return
        if buddy.startswith('/org/laptop/Sugar/Presence/Buddies/'):
            buddy = '.../' + buddy[35:]
        self.ps_watcher.log('INFO: Activity %s emitted BuddyJoined("%s")',
                            self.object_path, buddy)
        self.buddies.append(buddy)
        self.ps_watcher.activities_list_store.set(self.iter, ACT_COL_BUDDIES,
                                                  ' '.join(self.buddies))

    def _on_buddy_left(self, buddy):
        if self.buddies is None:
            return
        if buddy.startswith('/org/laptop/Sugar/Presence/Buddies/'):
            buddy = '.../' + buddy[35:]
        self.ps_watcher.log('INFO: Activity %s emitted BuddyLeft("%s")',
                            self.object_path, buddy)
        try:
            self.buddies.remove(buddy)
        except ValueError:
            pass
        self.ps_watcher.activities_list_store.set(self.iter, ACT_COL_BUDDIES,
                                                  ' '.join(self.buddies))

    def _on_get_buddies_success(self, buddies):
        self.buddies = []
        for buddy in buddies:
            self._on_buddy_joined(buddy)

    def _on_get_buddies_failure(self, e):
        self.log('ERROR: <Activity %s>.GetJoinedBuddies(): %s',
                 self.object_path, e)
        self.ps_watcher.activities_list_store.set(self.iter, ACT_COL_BUDDIES,
                                                  '!')

    def _on_new_channel(self, channel):
        if self.channels is None:
            return
        if channel.startswith(self.full_conn):
            channel = '...' + channel[len(self.full_conn):]
        self.ps_watcher.log('INFO: Activity %s emitted NewChannel("%s")',
                            self.object_path, channel)
        self.channels.append(channel)
        # FIXME: listen for Telepathy Closed signal!
        self.ps_watcher.activities_list_store.set(self.iter, ACT_COL_CHANNELS,
                                                  ' '.join(self.channels))

    def _on_get_channels_success(self, service, conn, channels):
        self.full_conn = conn
        if conn.startswith('/org/freedesktop/Telepathy/Connection/'):
            self.conn = '.../' + conn[38:]
        else:
            self.conn = conn
        self.ps_watcher.activities_list_store.set(self.iter, ACT_COL_CONN,
                                                  self.conn)
        self.channels = []
        for channel in channels:
            self._on_new_channel(channel)
        self.ps_watcher.activities_list_store.set(self.iter, ACT_COL_CHANNELS,
                                                  ' '.join(self.channels))

    def _on_get_channels_failure(self, e):
        self.ps_watcher.log('ERROR: <Activity %s>.GetChannels(): %s',
                            self.object_path, e)
        self.ps_watcher.activities_list_store.set(self.iter, ACT_COL_CONN,
                                                  '!')
        self.ps_watcher.activities_list_store.set(self.iter, ACT_COL_CHANNELS,
                                                  '!')

    def _on_get_id_success(self, ident):
        self.id = ident
        self.ps_watcher.activities_list_store.set(self.iter, ACT_COL_ID, ident)

    def _on_get_id_failure(self, e):
        self.ps_watcher.log('ERROR: <Activity %s>.GetId(): %s',
                            self.object_path, e)
        self.ps_watcher.activities_list_store.set(self.iter, ACT_COL_ID,
                                                  '!')

    def _on_get_color_success(self, color):
        self.color = color
        self.ps_watcher.activities_list_store.set(self.iter, ACT_COL_COLOR,
                                                  color)

    def _on_get_color_failure(self, e):
        self.ps_watcher.log('ERROR: <Activity %s>.GetColor(): %s',
                            self.object_path, e)
        self.ps_watcher.activities_list_store.set(self.iter, ACT_COL_COLOR,
                                                  '!')

    def _on_get_type_success(self, type_):
        self.type = type_
        self.ps_watcher.activities_list_store.set(self.iter, ACT_COL_TYPE,
                                                  type_)

    def _on_get_type_failure(self, e):
        self.ps_watcher.log('ERROR: <Activity %s>.GetType(): %s',
                            self.object_path, e)
        self.ps_watcher.activities_list_store.set(self.iter, ACT_COL_TYPE,
                                                  '!')

    def _on_get_name_success(self, name):
        self.name = name
        self.ps_watcher.activities_list_store.set(self.iter, ACT_COL_NAME,
                                                  name)

    def _on_get_name_failure(self, e):
        self.ps_watcher.log('ERROR: <Activity %s>.GetName(): %s',
                            self.object_path, e)
        self.ps_watcher.activities_list_store.set(self.iter, ACT_COL_NAME,
                                                  '!')

    def _finish_appearing(self):
        self.appearing = False
        self.ps_watcher.activities_list_store.set(self.iter, ACT_COL_WEIGHT,
                                                  400)
        return False

    def disappear(self):
        self.disappearing = True
        self.ps_watcher.activities_list_store.set(self.iter, ACT_COL_STRIKE,
                                                  True)
        timeout_add(5000, self._finish_disappearing)

    def _finish_disappearing(self):
        self.ps_watcher.remove_activity(self)
        return False


class BuddyWatcher(object):

    def __init__(self, ps_watcher, object_path):
        self.ps_watcher = ps_watcher
        self.bus = ps_watcher.bus
        self.proxy = self.bus.get_object(self.ps_watcher.unique_name,
                                         object_path)
        self.iface = dbus.Interface(self.proxy, BUDDY_IFACE)
        self.object_path = object_path
        self.appearing = True
        self.disappearing = False
        timeout_add(5000, self._finish_appearing)

        self.nick = '?'
        self.owner = False
        self.color = '?'
        self.ipv4 = '?'
        self.cur_act = '?'
        self.keyid = '?'
        self.activities = None
        self.handles = None

        self.iter = self.ps_watcher.add_buddy(self)

        self.iface.GetProperties(reply_handler=self._on_get_props_success,
                                 error_handler=self._on_get_props_failure,
                                 byte_arrays=True)

        self.iface.connect_to_signal('JoinedActivity', self._on_joined)
        self.iface.connect_to_signal('LeftActivity', self._on_left)
        self.iface.GetJoinedActivities(reply_handler=self._on_get_acts_success,
                                       error_handler=self._on_get_acts_failure)

        self.iface.connect_to_signal('TelepathyHandleAdded',
                                    self._on_handle_added)
        self.iface.connect_to_signal('TelepathyHandleRemoved',
                                    self._on_handle_removed)
        self.iface.GetTelepathyHandles(
                reply_handler=self._on_get_handles_success,
                error_handler=self._on_get_handles_failure)

    def _on_handle_added(self, service, conn, handle):
        if self.handles is None:
            return
        self.ps_watcher.log('INFO: Buddy %s emitted HandleAdded("%s", '
                            '"%s", %u)', self.object_path, service, conn,
                            handle)
        if conn.startswith('/org/freedesktop/Telepathy/Connection/'):
            conn = '.../' + conn[38:]
        self.handles.append('%u@%s' % (handle, conn))
        self.ps_watcher.buddies_list_store.set(self.iter,
                                               BUDDY_COL_HANDLES,
                                               ' '.join(self.handles))

    def _on_handle_removed(self, service, conn, handle):
        if self.handles is None:
            return
        if conn.startswith('/org/freedesktop/Telepathy/Connection/'):
            conn = '.../' + conn[38:]
        self.ps_watcher.log('INFO: Buddy %s emitted HandleRemoved("%s", '
                            '"%s", %u)', self.object_path, service, conn,
                            handle)
        try:
            self.handles.remove('%u@%s' % (handle, conn))
        except ValueError:
            pass
        self.ps_watcher.buddies_list_store.set(self.iter, BUDDY_COL_HANDLES,
                                               ' '.join(self.handles))

    def _on_get_handles_success(self, handles):
        self.handles = []
        for service, conn, handle in handles:
            self._on_handle_added(service, conn, handle)

    def _on_get_handles_failure(self, e):
        self.log('ERROR: <Buddy %s>.GetTelepathyHandles(): %s',
                 self.object_path, e)
        self.ps_watcher.buddies_list_store.set(self.iter, BUDDY_COL_HANDLES,
                                               '!')

    def _on_joined(self, act):
        if self.activities is None:
            return
        if act.startswith('/org/laptop/Sugar/Presence/Activities/'):
            act = '.../' + act[38:]
        self.ps_watcher.log('INFO: Buddy %s emitted ActivityJoined("%s")',
                            self.object_path, act)
        self.activities.append(act)
        self.ps_watcher.buddies_list_store.set(self.iter,
                                               BUDDY_COL_ACTIVITIES,
                                               ' '.join(self.activities))

    def _on_left(self, act):
        if self.activities is None:
            return
        if act.startswith('/org/laptop/Sugar/Presence/Activities/'):
            act = '.../' + act[38:]
        self.ps_watcher.log('INFO: Buddy %s emitted ActivityLeft("%s")',
                            self.object_path, act)
        try:
            self.activities.remove(act)
        except ValueError:
            pass
        self.ps_watcher.buddies_list_store.set(self.iter, BUDDY_COL_ACTIVITIES,
                                               ' '.join(self.activities))

    def _on_get_acts_success(self, activities):
        self.activities = []
        for act in activities:
            self._on_joined(act)

    def _on_get_acts_failure(self, e):
        self.log('ERROR: <Buddy %s>.GetJoinedActivities(): %s',
                 self.object_path, e)
        self.ps_watcher.buddies_list_store.set(self.iter, BUDDY_COL_ACTIVITIES,
                                               '!')

    def _on_get_props_success(self, props):
        # ignore key for now
        self.nick = props.get('nick', '?')
        self.owner = props.get('owner', False)
        self.color = props.get('color', '?')
        self.ipv4 = props.get('ip4-address', '?')
        self.ipv4 = props.get('ip4-address', '?')
        self.cur_act = props.get('current-activity', '?')
        key = props.get('key', None)
        if key is not None:
            self.keyid = sha1(key).hexdigest()[:8] + '...'
        else:
            self.keyid = '?'
        self.ps_watcher.buddies_list_store.set(self.iter, BUDDY_COL_NICK,
                                               self.nick)
        self.ps_watcher.buddies_list_store.set(self.iter, BUDDY_COL_OWNER,
                                               self.owner)
        self.ps_watcher.buddies_list_store.set(self.iter, BUDDY_COL_COLOR,
                                               self.color)
        self.ps_watcher.buddies_list_store.set(self.iter, BUDDY_COL_IP4,
                                               self.ipv4)
        self.ps_watcher.buddies_list_store.set(self.iter, BUDDY_COL_CUR_ACT,
                                               self.cur_act)
        self.ps_watcher.buddies_list_store.set(self.iter, BUDDY_COL_KEY_ID,
                                               self.keyid)

    def _on_get_props_failure(self, e):
        self.ps_watcher.log('ERROR: <Buddy %s>.GetProperties(): %s',
                            self.object_path, e)
        self.ps_watcher.buddies_list_store.set(self.iter, BUDDY_COL_NICK, '!')
        self.ps_watcher.buddies_list_store.set(self.iter, BUDDY_COL_OWNER,
                                               False)
        self.ps_watcher.buddies_list_store.set(self.iter, BUDDY_COL_COLOR, '!')
        self.ps_watcher.buddies_list_store.set(self.iter, BUDDY_COL_IP4, '!')
        self.ps_watcher.buddies_list_store.set(self.iter, BUDDY_COL_CUR_ACT,
                                               '!')
        self.ps_watcher.buddies_list_store.set(self.iter, BUDDY_COL_KEY_ID,
                                               '!')

    def _finish_appearing(self):
        self.appearing = False
        self.ps_watcher.buddies_list_store.set(self.iter, BUDDY_COL_WEIGHT,
                                               400)
        return False

    def disappear(self):
        self.disappearing = True
        self.ps_watcher.buddies_list_store.set(self.iter, BUDDY_COL_STRIKE,
                                               True)
        timeout_add(5000, self._finish_disappearing)

    def _finish_disappearing(self):
        self.ps_watcher.remove_buddy(self)
        return False


class PresenceServiceWatcher(VBox):

    def __init__(self, bus, unique_name, log):
        VBox.__init__(self)

        self.bus = bus
        self.unique_name = unique_name
        self.proxy = bus.get_object(unique_name, PS_PATH)
        self.iface = dbus.Interface(self.proxy, PS_IFACE)
        self.log = log

        self.activities = None
        self.iface.connect_to_signal('ActivityAppeared',
                                     self._on_activity_appeared)
        self.iface.connect_to_signal('ActivityDisappeared',
                                     self._on_activity_disappeared)
        self.iface.GetActivities(reply_handler=self._on_get_activities_success,
                                 error_handler=self._on_get_activities_failure)

        self.buddies = None
        self.iface.connect_to_signal('BuddyAppeared',
                                     self._on_buddy_appeared)
        self.iface.connect_to_signal('BuddyDisappeared',
                                     self._on_buddy_disappeared)
        self.iface.GetBuddies(reply_handler=self._on_get_buddies_success,
                              error_handler=self._on_get_buddies_failure)

        # keep this in sync with the ACT_COL_ constants
        self.activities_list_store = ListStore(str,     # object path
                                               int,     # weight (bold if new)
                                               bool,    # strikethrough (dead)
                                               str,     # ID
                                               str,     # color
                                               str,     # type
                                               str,     # name
                                               str,     # conn
                                               str,     # channels
                                               str,     # buddies
                                               )

        self.pack_start(Label('Activities:'), False, False)

        self.activities_list = TreeView(self.activities_list_store)
        c = self.activities_list.insert_column_with_attributes(0,
            'Object path', CellRendererText(), text=ACT_COL_PATH,
            weight=ACT_COL_WEIGHT, strikethrough=ACT_COL_STRIKE)
        c.set_resizable(True)
        c.set_sort_column_id(ACT_COL_PATH)
        c = self.activities_list.insert_column_with_attributes(1, 'ID',
            CellRendererText(), text=ACT_COL_ID,
            weight=ACT_COL_WEIGHT, strikethrough=ACT_COL_STRIKE)
        c.set_resizable(True)
        c.set_sort_column_id(ACT_COL_ID)
        c = self.activities_list.insert_column_with_attributes(2, 'Color',
            CellRendererText(), text=ACT_COL_COLOR,
            weight=ACT_COL_WEIGHT, strikethrough=ACT_COL_STRIKE)
        c.set_resizable(True)
        c.set_sort_column_id(ACT_COL_COLOR)
        c = self.activities_list.insert_column_with_attributes(3, 'Type',
            CellRendererText(), text=ACT_COL_TYPE, weight=ACT_COL_WEIGHT,
            strikethrough=ACT_COL_STRIKE)
        c.set_resizable(True)
        c.set_sort_column_id(ACT_COL_TYPE)
        c = self.activities_list.insert_column_with_attributes(4, 'Name',
            CellRendererText(), text=ACT_COL_NAME, weight=ACT_COL_WEIGHT,
            strikethrough=ACT_COL_STRIKE)
        c.set_resizable(True)
        c.set_sort_column_id(ACT_COL_NAME)
        c = self.activities_list.insert_column_with_attributes(5, 'Connection',
            CellRendererText(), text=ACT_COL_CONN, weight=ACT_COL_WEIGHT,
            strikethrough=ACT_COL_STRIKE)
        c.set_resizable(True)
        c.set_sort_column_id(ACT_COL_CONN)
        c = self.activities_list.insert_column_with_attributes(6, 'Channels',
            CellRendererText(), text=ACT_COL_CHANNELS, weight=ACT_COL_WEIGHT,
            strikethrough=ACT_COL_STRIKE)
        c.set_resizable(True)
        c = self.activities_list.insert_column_with_attributes(7, 'Buddies',
            CellRendererText(), text=ACT_COL_BUDDIES, weight=ACT_COL_WEIGHT,
            strikethrough=ACT_COL_STRIKE)
        c.set_resizable(True)

        scroller = ScrolledWindow()
        scroller.add(self.activities_list)
        self.pack_start(scroller)

        # keep this in sync with the BUDDY_COL_ constants
        self.buddies_list_store = ListStore(str, int, bool, str, bool,
                                            str, str, str, str, str, str)

        self.pack_start(Label('Buddies:'), False, False)
        self.buddies_list = TreeView(self.buddies_list_store)
        c = self.buddies_list.insert_column_with_attributes(0, 'Object path',
            CellRendererText(), text=BUDDY_COL_PATH,
            weight=BUDDY_COL_WEIGHT, strikethrough=BUDDY_COL_STRIKE)
        c.set_resizable(True)
        c.set_sort_column_id(BUDDY_COL_PATH)
        c = self.buddies_list.insert_column_with_attributes(1, 'Key ID',
            CellRendererText(), text=BUDDY_COL_KEY_ID,
            weight=BUDDY_COL_WEIGHT, strikethrough=BUDDY_COL_STRIKE)
        c.set_resizable(True)
        c.set_sort_column_id(BUDDY_COL_KEY_ID)
        c = self.buddies_list.insert_column_with_attributes(2, 'Nick',
            CellRendererText(), text=BUDDY_COL_NICK,
            weight=BUDDY_COL_WEIGHT, strikethrough=BUDDY_COL_STRIKE)
        c.set_resizable(True)
        c.set_sort_column_id(BUDDY_COL_NICK)
        c = self.buddies_list.insert_column_with_attributes(3, 'Owner',
            CellRendererToggle(), active=BUDDY_COL_OWNER)
        c = self.buddies_list.insert_column_with_attributes(4, 'Color',
            CellRendererText(), text=BUDDY_COL_COLOR,
            weight=BUDDY_COL_WEIGHT, strikethrough=BUDDY_COL_STRIKE)
        c.set_resizable(True)
        c.set_sort_column_id(BUDDY_COL_OWNER)
        c = self.buddies_list.insert_column_with_attributes(5, 'IPv4',
            CellRendererText(), text=BUDDY_COL_IP4,
            weight=BUDDY_COL_WEIGHT, strikethrough=BUDDY_COL_STRIKE)
        c.set_resizable(True)
        c.set_sort_column_id(BUDDY_COL_IP4)
        c = self.buddies_list.insert_column_with_attributes(6, 'CurAct',
            CellRendererText(), text=BUDDY_COL_CUR_ACT,
            weight=BUDDY_COL_WEIGHT, strikethrough=BUDDY_COL_STRIKE)
        c.set_resizable(True)
        c.set_sort_column_id(BUDDY_COL_CUR_ACT)
        c = self.buddies_list.insert_column_with_attributes(7, 'Activities',
            CellRendererText(), text=BUDDY_COL_ACTIVITIES,
            weight=BUDDY_COL_WEIGHT, strikethrough=BUDDY_COL_STRIKE)
        c.set_resizable(True)
        c.set_sort_column_id(BUDDY_COL_ACTIVITIES)
        c = self.buddies_list.insert_column_with_attributes(8, 'Handles',
            CellRendererText(), text=BUDDY_COL_HANDLES,
            weight=BUDDY_COL_WEIGHT, strikethrough=BUDDY_COL_STRIKE)
        c.set_resizable(True)
        c.set_sort_column_id(BUDDY_COL_HANDLES)

        scroller = ScrolledWindow()
        scroller.add(self.buddies_list)
        self.pack_start(scroller)

        self.iface.connect_to_signal('ActivityInvitation',
                                     self._on_activity_invitation)
        self.iface.connect_to_signal('PrivateInvitation',
                                     self._on_private_invitation)

    def _on_get_activities_success(self, paths):
        self.log('INFO: PS GetActivities() returned %r', paths)
        self.activities = {}
        for path in paths:
            self.activities[path] = ActivityWatcher(self, path)

    def _on_get_activities_failure(self, e):
        self.log('ERROR: PS GetActivities() failed with %s', e)

    def add_activity(self, act):
        path = act.object_path
        if path.startswith('/org/laptop/Sugar/Presence/Activities/'):
            path = '.../' + path[38:]
        return self.activities_list_store.append((path, 700, False,
            act.id, act.color, act.type, act.name, act.conn, '?', '?'))

    def remove_activity(self, act):
        self.activities.pop(act.object_path, None)
        self.activities_list_store.remove(act.iter)

    def _on_activity_appeared(self, path):
        if self.activities is None:
            return
        self.log('INFO: PS emitted ActivityAppeared("%s")', path)
        self.activities[path] = ActivityWatcher(self, path)

    def _on_activity_disappeared(self, path):
        if self.activities is None:
            return
        self.log('INFO: PS emitted ActivityDisappeared("%s")', path)
        act = self.activities.get(path)
        if act is None:
            self.log('WARNING: Trying to remove activity "%s" which is '
                     'already absent', path)
        else:
            # we don't remove the activity straight away, just cross it out
            act.disappear()

    def _on_activity_invitation(self, path):
        self.log('INFO: PS emitted ActivityInvitation("%s")', path)

    def _on_private_invitation(self, bus_name, conn, channel):
        self.log('INFO: PS emitted PrivateInvitation("%s", "%s", "%s")',
                 bus_name, conn, channel)

    def _on_get_buddies_success(self, paths):
        self.log('INFO: PS GetBuddies() returned %r', paths)
        self.buddies = {}
        for path in paths:
            self.buddies[path] = BuddyWatcher(self, path)

    def _on_get_buddies_failure(self, e):
        self.log('ERROR: PS GetBuddies() failed with %s', e)

    def add_buddy(self, b):
        path = b.object_path
        if path.startswith('/org/laptop/Sugar/Presence/Buddies/'):
            path = '.../' + path[35:]
        return self.buddies_list_store.append((path, 700, False,
            b.nick, b.owner, b.color, b.ipv4, b.cur_act, b.keyid,
            '?', '?'))

    def remove_buddy(self, b):
        self.buddies.pop(b.object_path, None)
        self.buddies_list_store.remove(b.iter)

    def _on_buddy_appeared(self, path):
        if self.buddies is None:
            return
        self.log('INFO: PS emitted BuddyAppeared("%s")', path)
        self.buddies[path] = BuddyWatcher(self, path)

    def _on_buddy_disappeared(self, path):
        if self.buddies is None:
            return
        self.log('INFO: PS emitted BuddyDisappeared("%s")', path)
        b = self.buddies.get(path)
        if b is None:
            self.log('ERROR: Trying to remove buddy "%s" which is already '
                     'absent', path)
        else:
            # we don't remove the activity straight away, just cross it out
            b.disappear()


class PresenceServiceNameWatcher(VBox):

    def __init__(self, bus):
        VBox.__init__(self)

        self.bus = bus

        self.label = Label('Looking for Presence Service...')
        self.errors = ListStore(str)

        errors = TreeView(model=self.errors)
        errors.insert_column_with_attributes(0, 'Log', CellRendererText(),
                                             text=0)
        scroller = ScrolledWindow()
        scroller.add(errors)

        self.paned = VPaned()
        self.paned.pack1(scroller)

        self.pack_start(self.label, False, False)
        self.pack_end(self.paned)

        bus.watch_name_owner(PS_NAME, self.on_name_owner_change)
        self.ps_watcher = Label('-')
        self.paned.pack2(self.ps_watcher)

        self.show_all()

    def log(self, format, *args):
        self.errors.append((format % args,))

    def on_name_owner_change(self, owner):
        try:
            if owner:
                self.label.set_text('Presence Service running: unique name %s'
                                    % owner)
                if self.ps_watcher is not None:
                    self.paned.remove(self.ps_watcher)
                self.ps_watcher = PresenceServiceWatcher(self.bus, owner,
                                                         self.log)
                self.paned.pack2(self.ps_watcher)
                self.show_all()
            else:
                self.label.set_text('Presence Service not running')
                if self.ps_watcher is not None:
                    self.paned.remove(self.ps_watcher)
                self.ps_watcher = Label('-')
                self.paned.pack2(self.ps_watcher)
        except Exception, e:
            self.log('ERROR: %s', e)


class Interface(object):
    def __init__(self):
        self.widget = PresenceServiceNameWatcher(dbus.SessionBus())
