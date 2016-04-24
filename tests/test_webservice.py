# Copyright (C) 2013, Walter Bender
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

import os
import sys
import unittest

from gi.repository import Gtk

from jarabe import config
from jarabe.webservice.account import Account
from jarabe.webservice import accountsmanager

ACCOUNT_NAME = 'mock'

tests_dir = os.getcwd()
extension_dir = os.path.join(tests_dir, 'extensions')
web_extension_dir = os.path.join(extension_dir, 'webservice')


class TestWebAccounts(unittest.TestCase):
    def setUp(self):
        os.environ["MOCK_ACCOUNT_STATE"] = str(Account.STATE_NONE)
        self.save_ext_path = config.ext_path
        config.ext_path = extension_dir
        sys.path.append(config.ext_path)

    def test_get_description(self):
        accounts = accountsmanager.get_all_accounts()
        found_mock_account = False
        for account in accounts:
            if account.get_description() == ACCOUNT_NAME:
                found_mock_account = True
                break
        self.assertTrue(found_mock_account)

    def test_icon_theme(self):
        icon_theme = Gtk.IconTheme.get_default()
        icon_search_path = icon_theme.get_search_path()
        icon_path = os.path.join(web_extension_dir, ACCOUNT_NAME, 'icons')
        self.assertTrue(icon_path in icon_search_path)

    def test_get_webaccount_services(self):
        services = accountsmanager.get_webaccount_services()
        self.assertTrue(len(services) > 0)

    def test_get_all_accounts(self):
        accounts = accountsmanager.get_all_accounts()
        self.assertTrue(len(accounts) > 0)

    def test_get_account(self):
        account = accountsmanager.get_account('mock')
        self.assertIsNotNone(account)

    def test_get_service(self):
        account = accountsmanager.get_service('mock')
        self.assertIsNotNone(account)

    def test_get_configured_accounts(self):
        os.environ["MOCK_ACCOUNT_STATE"] = str(Account.STATE_VALID)
        accounts = accountsmanager.get_configured_accounts()
        count = len(accounts)
        self.assertTrue(count > 0)

        self.assertTrue(accountsmanager.has_configured_accounts())

        os.environ["MOCK_ACCOUNT_STATE"] = str(Account.STATE_NONE)
        accounts = accountsmanager.get_configured_accounts()
        self.assertTrue(len(accounts) == count - 1)

        os.environ["MOCK_ACCOUNT_STATE"] = str(Account.STATE_EXPIRED)
        accounts = accountsmanager.get_configured_accounts()
        self.assertTrue(len(accounts) == count)

    def test_get_active_accounts(self):
        os.environ["MOCK_ACCOUNT_STATE"] = str(Account.STATE_VALID)
        accounts = accountsmanager.get_active_accounts()
        count = len(accounts)
        self.assertTrue(count > 0)

        os.environ["MOCK_ACCOUNT_STATE"] = str(Account.STATE_EXPIRED)
        accounts = accountsmanager.get_active_accounts()
        self.assertTrue(len(accounts) == count - 1)

    def test_share_menu(self):
        accounts = accountsmanager.get_all_accounts()
        for account in accounts:
            shared_journal_entry = account.get_shared_journal_entry()
            share_menu = shared_journal_entry.get_share_menu(
                {'account': 'mock'})
            self.assertIsNotNone(share_menu)

    def test_refresh_menu(self):
        accounts = accountsmanager.get_all_accounts()
        for account in accounts:
            shared_journal_entry = account.get_shared_journal_entry()
            refresh_menu = shared_journal_entry.get_refresh_menu()
            self.assertIsNotNone(refresh_menu)

    def tearDown(self):
        sys.path.remove(config.ext_path)
        config.ext_path = self.save_ext_path
