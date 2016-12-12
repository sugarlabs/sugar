# Copyright (c) 2013 Walter Bender, Raul Gutierrez Segales
# Copyright (c) 2013 SugarLabs
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

from gi.repository import GObject


class Account():
    ''' Account is a prototype class for online accounts. It provides
    stubs for public methods that are used by online services.
    '''

    STATE_NONE = 0
    STATE_VALID = 1
    STATE_EXPIRED = 2

    def get_description(self):
        ''' get_description returns a brief description of the online
        service. The description is used in palette menuitems and on
        the webservices control panel.

        :returns: online-account name
        :rtype: string
        '''
        raise NotImplementedError

    def get_token_state(self):
        ''' get_token_state returns an enum to describe the state of
        the online service:
        State.NONE means there is no token, e.g., the service is not
            configured.
        State.VALID means there is a valid token, e.g., the service is
            available for use.
        State.EXPIRED means the token is no longer valid.

        :returns: token state
        :rtype: enum
        '''
        raise NotImplementedError

    def get_shared_journal_entry(self):
        ''' get_shared_journal_entry returns a class used to
        intermediate between the online service and the Sugar UI
        elements.

        :returns: SharedJournalEntry()
        :rtype: SharedJournalEntry
        '''
        return NotImplemented


class SharedJournalEntry():
    ''' SharedJournalEntry is a class used to intermediate between the
    online service and the Sugar UI elements (MenuItems used in the
    Journal UI) for online accounts. It provides stubs for public
    methods that are used by online services.

    The comments-changed signal is emitted by the online service if
    changes to the 'comments' metadata have been made.

    :emits: metadata['comments']
    :type: string
    '''

    __gsignals__ = {
        'comments-changed': (GObject.SignalFlags.RUN_FIRST, None, ([str]))
    }

    def get_share_menu(self, get_uid_list):
        ''' get_share_menu returns a menu item used on the Copy To
        palette in the Journal and on the Journal detail-view toolbar.

        :param: journal_entry_get_uid_list
        :type: bound method
        :returns: MenuItem
        :rtype: MenuItem
        '''
        raise NotImplementedError

    def get_refresh_menu(self):
        ''' get_refresh_menu returns a menu item used on the Journal
        detail-view toolbar.

        :returns: MenuItem
        :rtype: MenuItem
        '''
        raise NotImplementedError

    def set_metadata(self, metadata):
        ''' The online account uses this method to set metadata in the
        Sugar journal and provide a means of updating menuitem status,
        e.g., enabling the refresh menu after a successful transfer.

        :param: journal_entry_metadata
        :type: dict
        '''
        raise NotImplementedError
