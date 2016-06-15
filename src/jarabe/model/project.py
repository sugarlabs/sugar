# Copyright (C) 2016 Abhijit Patel
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
import dbus

from gi.repository import GObject


from sugar3 import util
from sugar3 import power
from sugar3.presence import presenceservice
from jarabe.journal.projectwrapper import ProjectWrapper

SCOPE_PRIVATE = 'private'
SCOPE_INVITE_ONLY = 'invite'  # shouldn't be shown in UI, it's implicit
SCOPE_NEIGHBORHOOD = 'public'

J_DBUS_SERVICE = 'org.laptop.Journal'
J_DBUS_PATH = '/org/laptop/Journal'
J_DBUS_INTERFACE = 'org.laptop.Journal'

N_BUS_NAME = 'org.freedesktop.Notifications'
N_OBJ_PATH = '/org/freedesktop/Notifications'
N_IFACE_NAME = 'org.freedesktop.Notifications'

CONN_INTERFACE_ACTIVITY_PROPERTIES = 'org.laptop.Telepathy.ActivityProperties'


class Project(GObject.GObject):

    __gsignals__ = {
        'shared': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'joined': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        # For internal use only, use can_close() if you want to perform extra
        # checks before actually closing
        '_closing': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, project_metadata):
        GObject.GObject.__init__(self)
        self.metadata = project_metadata
        self._id = self.metadata['activity_id']
        self._bundle_id = 'org.sugarlabs.Project'

        self.shared_activity = None
        self._invites_queue = []
        self._collab = ProjectWrapper(self)
        self._collab.message.connect(self.__message_cb)
        self._collab.setup()

    def get_id(self):
        return self._id

    def get_bundle_id(self):
        return self._bundle_id

    def _invite_response_cb(self, error):
        if error:
            logging.error('Invite failed: %s', error)

    def __message_cb(self, collab, buddy, msg):
        action = msg.get('action')
        text = msg.get('text', 'Lol')
        logging.debug('Project.__message_cb %r' %text)
        if action != 'text':
            return

    def send_event(self, text):
        logging.debug('Project.send_event %r' %text)
        self._collab.post(dict(action='text', text=text))

    def _send_invites(self):
        while self._invites_queue:
            logging.debug('[GSoC]Project._send_invites')
            account_path, contact_id = self._invites_queue.pop()
            pservice = presenceservice.get_instance()
            buddy = pservice.get_buddy(account_path, contact_id)
            if buddy:
                logging.debug('[GSoC]Project._send_invites %r' %buddy.props.nick)
                self.shared_activity.invite(
                    buddy, '', self._invite_response_cb)
            else:
                logging.error('Cannot invite %s %s, no such buddy',
                              account_path, contact_id)


    def invite(self, account_path, contact_id):
        self._invites_queue.append((account_path, contact_id))
        logging.debug('[GSoC]Project._invite')
        if (self.shared_activity is None
            or not self.shared_activity.props.joined):
            self.share(True)
        else:
            self._send_invites()

    def share(self, private=False):
        '''
        Request that the activity be shared on the network.
        Args:
            private (bool): True to share by invitation only,
            False to advertise as shared to everyone.

        Once the activity is shared, its privacy can be changed by setting
        its 'private' property.
        '''
        if self.shared_activity and self.shared_activity.props.joined:
            raise RuntimeError('Activity %s already shared.' %
                               self._id)
        logging.debug('[GSoC]Project.share')
        verb = private and 'private' or 'public'
        logging.debug('Requesting %s share of activity %s.' % (verb,
                      self._id))
        pservice = presenceservice.get_instance()
        pservice.connect('activity-shared', self.__share_cb)
        pservice.share_activity(self, private=private)

    def __share_cb(self, ps, success, activity, err):
        logging.debug('Project.__share_cb %r' %success)
        if not success:
            logging.debug('Share of activity %s failed: %s.' %
                          (self._id, err))
            return

        logging.debug('Share of activity %s successful, PS activity is %r.' %
                     (self._id, activity))

        activity.props.name = self.metadata['title']

        power_manager = power.get_power_manager()
        if power_manager.suspend_breaks_collaboration():
            power_manager.inhibit_suspend()
        self.shared_activity = activity
        self.shared_activity.connect('notify::private',
                                     self.__privacy_changed_cb)
        self.emit('shared')
        self.__privacy_changed_cb(self.shared_activity, None)
        self._send_invites()

    def __privacy_changed_cb(self, shared_activity, param_spec):
        logging.debug('__privacy_changed_cb %r' %
                      shared_activity.props.private)
        if shared_activity.props.private:
            self.metadata['share-scope'] = SCOPE_INVITE_ONLY
        else:
            self.metadata['share-scope'] = SCOPE_NEIGHBORHOOD
