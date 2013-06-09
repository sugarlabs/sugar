#!/usr/bin/env python
#
# Copyright (c) 2013 Walter Bender

#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:

#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import os

from sugar3.graphics.menuitem import MenuItem
from jarabe.web import account

ACCOUNT_NAME = 'mock'


class MockAccount(account.Account):
    def __init__(self):
        return

    def get_description(self):
        return ACCOUNT_NAME

    def get_shared_journal_entry():
        return MockSharedJournalEntry()

    def get_token_state(self):
        return os.environ["MOCK_ACCOUNT_STATE"]


class MockSharedJournalEnrty(account.SharedJournalEntry):
    def __init__(self):
        return

    def get_share_menu(self, journal_entry_metadata):
        share_menu = MenuItem()
        return share_menu

    def get_refresh_menu(self):
        refresh_menu = MenuItem()
        return refresh_menu

    def set_metadata(self, metadata):
        return


def get_account():
    return MockAccount()