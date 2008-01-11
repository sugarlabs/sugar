"""Shell side object which manages request to start activity"""
# Copyright (C) 2006-2007 Red Hat, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import logging
import subprocess
import signal

import dbus
import gobject

from sugar.presence import presenceservice
from sugar.activity.activityhandle import ActivityHandle
from sugar.activity import registry
from sugar import util
from sugar import env

from errno import EEXIST

import os

# #3903 - this constant can be removed and assumed to be 1 when dbus-python
# 0.82.3 is the only version used
if dbus.version >= (0, 82, 3):
    DBUS_PYTHON_TIMEOUT_UNITS_PER_SECOND = 1
else:
    DBUS_PYTHON_TIMEOUT_UNITS_PER_SECOND = 1000

_SHELL_SERVICE = "org.laptop.Shell"
_SHELL_PATH = "/org/laptop/Shell"
_SHELL_IFACE = "org.laptop.Shell"

_DS_SERVICE = "org.laptop.sugar.DataStore"
_DS_INTERFACE = "org.laptop.sugar.DataStore"
_DS_PATH = "/org/laptop/sugar/DataStore"

_ACTIVITY_FACTORY_INTERFACE = "org.laptop.ActivityFactory"

_RAINBOW_SERVICE_NAME = "org.laptop.security.Rainbow"
_RAINBOW_ACTIVITY_FACTORY_PATH = "/"
_RAINBOW_ACTIVITY_FACTORY_INTERFACE = "org.laptop.security.Rainbow"

_children_pid = []

def _sigchild_handler(signum, frame):
    for child_pid in _children_pid:
        pid, status = os.waitpid(child_pid, os.WNOHANG)
        if pid > 0:
            _children_pid.remove(pid)

signal.signal(signal.SIGCHLD, _sigchild_handler)

def create_activity_id():
    """Generate a new, unique ID for this activity"""
    pservice = presenceservice.get_instance()

    # create a new unique activity ID
    i = 0
    act_id = None
    while i < 10:
        act_id = util.unique_id()
        i += 1

        # check through network activities
        found = False
        activities = pservice.get_activities()
        for act in activities:
            if act_id == act.props.id:
                found = True
                break
        if not found:
            return act_id
    raise RuntimeError("Cannot generate unique activity id.")

def get_environment(activity):
    environ = os.environ.copy()

    bin_path = os.path.join(activity.path, 'bin')

    activity_root = env.get_profile_path(activity.bundle_id)
    if not os.path.exists(activity_root):
        os.mkdir(activity_root)

    data_dir = os.path.join(activity_root, 'instance')
    if not os.path.exists(data_dir):
        os.mkdir(data_dir)

    data_dir = os.path.join(activity_root, 'data')
    if not os.path.exists(data_dir):
        os.mkdir(data_dir)

    tmp_dir = os.path.join(activity_root, 'tmp')
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)

    environ['SUGAR_BUNDLE_PATH'] = activity.path
    environ['SUGAR_BUNDLE_ID']   = activity.bundle_id
    environ['SUGAR_ACTIVITY_ROOT'] = activity_root
    environ['PATH'] = bin_path + ':' + environ['PATH']
    #environ['RAINBOW_STRACE_LOG'] = '1'

    if activity.bundle_id in [ 'org.laptop.WebActivity', 
                               'org.laptop.GmailActivity',
                               'org.laptop.WikiBrowseActivity'
                               ]:
        environ['RAINBOW_CONSTANT_UID'] = 'yes'

    return environ

def get_command(activity, activity_id=None, object_id=None, uri=None):
    if not activity_id:
        activity_id = create_activity_id()

    command = activity.command.split(' ')
    command.extend(['-b', activity.bundle_id])
    command.extend(['-a', activity_id])

    if object_id is not None:
        command.extend(['-o', object_id])
    if uri is not None:
        command.extend(['-u', uri])

    print command

    return command

def open_log_file(activity):
    i = 1
    while True:
        path = env.get_logs_path('%s-%s.log' % (activity.bundle_id, i))
        try:
            fd = os.open(path, os.O_EXCL | os.O_CREAT \
                             | os.O_SYNC | os.O_WRONLY, 0644)
            f = os.fdopen(fd, 'w', 0)
            return (path, f)
        except OSError, e:
            if e.errno == EEXIST:
                i += 1
            else:
                raise e

class ActivityCreationHandler(gobject.GObject):
    """Sugar-side activity creation interface

    This object uses a dbus method on the ActivityFactory
    service to create the new activity.  It generates
    GObject events in response to the success/failure of
    activity startup using callbacks to the service's
    create call.
    """

    def __init__(self, service_name, handle):
        """Initialise the handler

        service_name -- the service name of the bundle factory
        activity_handle -- stores the values which are to
            be passed to the service to uniquely identify
            the activity to be created and the sharing
            service that may or may not be connected with it

            sugar.activity.activityhandle.ActivityHandle instance

        calls the "create" method on the service for this
        particular activity type and registers the
        _reply_handler and _error_handler methods on that
        call's results.

        The specific service which creates new instances of this
        particular type of activity is created during the activity
        registration process in shell bundle registry which creates
        service definition files for each registered bundle type.

        If the file '/etc/olpc-security' exists, then activity launching
        will be delegated to the prototype 'Rainbow' security service.
        """
        gobject.GObject.__init__(self)

        self._service_name = service_name
        self._handle = handle

        self._use_rainbow = os.path.exists('/etc/olpc-security')
        if service_name in [ 'org.laptop.JournalActivity',
                             'org.laptop.Terminal',
                             'org.laptop.LogViewer',
                             'org.laptop.Analyze'
                             ]:
            self._use_rainbow = False                    
    
        bus = dbus.SessionBus()

        bus_object = bus.get_object(_SHELL_SERVICE, _SHELL_PATH)
        self._shell = dbus.Interface(bus_object, _SHELL_IFACE)

        if handle.activity_id is not None and \
           handle.object_id is None:
            datastore = dbus.Interface(
                    bus.get_object(_DS_SERVICE, _DS_PATH), _DS_INTERFACE)
            datastore.find({ 'activity_id': self._handle.activity_id }, [],
                           reply_handler=self._find_object_reply_handler,
                           error_handler=self._find_object_error_handler)
        else:
            self._launch_activity()

    def _launch_activity(self):
        if self._handle.activity_id != None:
            self._shell.ActivateActivity(self._handle.activity_id,
                        reply_handler=self._activate_reply_handler,
                        error_handler=self._activate_error_handler)
        else:
            self._create_activity()

    def _create_activity(self):
        if self._handle.activity_id is None:
            self._handle.activity_id = create_activity_id()

        self._shell.NotifyLaunch(
                    self._service_name, self._handle.activity_id,
                    reply_handler=self._no_reply_handler,
                    error_handler=self._notify_launch_error_handler)

        activity_registry = registry.get_registry()
        activity = activity_registry.get_activity(self._service_name)
        if activity:
            environ = get_environment(activity)
            (log_path, log_file) = open_log_file(activity)
            command = get_command(activity, self._handle.activity_id,
                                  self._handle.object_id,
                                  self._handle.uri)

            if not self._use_rainbow:
                p = subprocess.Popen(command, env=environ, cwd=activity.path,
                                     stdout=log_file, stderr=log_file)
                _children_pid.append(p.pid)
            else:
                log_file.close()
                system_bus = dbus.SystemBus()
                factory = system_bus.get_object(_RAINBOW_SERVICE_NAME,
                                                _RAINBOW_ACTIVITY_FACTORY_PATH)
                factory.CreateActivity(
                        log_path,
                        environ,
                        command,
                        environ['SUGAR_BUNDLE_PATH'],
                        environ['SUGAR_BUNDLE_ID'],
                        timeout=30 * DBUS_PYTHON_TIMEOUT_UNITS_PER_SECOND,
                        reply_handler=self._create_reply_handler,
                        error_handler=self._create_error_handler,
                        dbus_interface=_RAINBOW_ACTIVITY_FACTORY_INTERFACE)

    def _no_reply_handler(self, *args):
        pass

    def _notify_launch_failure_error_handler(self, err):
        logging.error('Notify launch failure failed %s' % err)

    def _notify_launch_error_handler(self, err):
        logging.debug('Notify launch failed %s' % err)

    def _activate_reply_handler(self, activated):
        if not activated:
            self._create_activity()

    def _activate_error_handler(self, err):
        logging.error("Activity activation request failed %s" % err)

    def _create_reply_handler(self):
        logging.debug("Activity created %s (%s)." %
            (self._handle.activity_id, self._service_name))

    def _create_error_handler(self, err):
        logging.error("Couldn't create activity %s (%s): %s" %
            (self._handle.activity_id, self._service_name, err))
        self._shell.NotifyLaunchFailure(
            self._handle.activity_id, reply_handler=self._no_reply_handler,
            error_handler=self._notify_launch_failure_error_handler)

    def _find_object_reply_handler(self, jobjects, count):
        if count > 0:
            if count > 1:
                logging.debug("Multiple objects has the same activity_id.")
            self._handle.object_id = jobjects[0]['uid']
        self._create_activity()

    def _find_object_error_handler(self, err):
        logging.error("Datastore find failed %s" % err)
        self._create_activity()

def create(service_name, activity_handle=None):
    """Create a new activity from its name."""
    if not activity_handle:
        activity_handle = ActivityHandle()
    return ActivityCreationHandler(service_name, activity_handle)

def create_with_uri(service_name, uri):
    """Create a new activity and pass the uri as handle."""
    activity_handle = ActivityHandle(uri=uri)
    return ActivityCreationHandler(service_name, activity_handle)

def create_with_object_id(service_name, object_id):
    """Create a new activity and pass the object id as handle."""
    activity_handle = ActivityHandle(object_id=object_id)
    return ActivityCreationHandler(service_name, activity_handle)
