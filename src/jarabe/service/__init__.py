import logging
import os
import shutil
import time

import dbus

from sugar.datastore import datastore
from sugar import env

from jarabe.service.session import get_session_manager
from jarabe.service.network import NMService
from jarabe.service.gui import UIService
from jarabe.service import logsmanager

def start_logsmanager():
    try:
        logsmanager.setup()
    except Exception, e:
        # logs setup is not critical; it should not prevent sugar from
        # starting if (for example) the disk is full or read-only.
        print 'Log setup failed: %s' % e

def start_datastore():
    # Mount the datastore in internal flash
    ds_path = env.get_profile_path('datastore')
    try:
        datastore.mount(ds_path, [], timeout=120)
    except Exception, e:
        # Don't explode if there's corruption; move the data out of the way
        # and attempt to create a store from scratch.
        logging.error(e)
        shutil.move(ds_path, os.path.abspath(ds_path) + str(time.time()))
        datastore.mount(ds_path, [], timeout=120)

def start_all():
    start_datastore()

    ui_service = UIService()
    ui_service.start()

    session_manager = get_session_manager()
    session_manager.start()

    try:
        nm_service = NMService()
    except dbus.DBusException:
        logging.error("Network manager is already running.")

