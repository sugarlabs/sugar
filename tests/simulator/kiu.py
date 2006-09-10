#!/usr/bin/python
import os
from sugar.session.TestSession import TestSession
from sugar.presence import PresenceService

os.environ['SUGAR_NICK_NAME'] = 'kiu'

session = TestSession()
session.start()

PresenceService.start()

