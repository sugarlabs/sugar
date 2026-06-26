# Copyright (C) 2006-2007 Red Hat, Inc.
# Copyright (C) 2010 Collabora Ltd. <http://www.collabora.co.uk/>
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

"""Shell side object which manages request to start activity

UNSTABLE. Activities are currently not allowed to run other activities so at
the moment there is no reason to stabilize this API.
"""

import logging
import dbus
from gi.repository import GObject
from gi.repository import GLib

from sugar4.activity.activityhandle import ActivityHandle
from sugar4 import util
from sugar4 import env
from sugar4.datastore import datastore

from errno import EEXIST, ENOSPC

import os
import subprocess

_SHELL_SERVICE = 'org.laptop.Shell'
_SHELL_PATH = '/org/laptop/Shell'
_SHELL_IFACE = 'org.laptop.Shell'

_ACTIVITY_FACTORY_INTERFACE = 'org.laptop.ActivityFactory'

# helper method to close all filedescriptors
# borrowed from subprocess.py
try:
    MAXFD = os.sysconf('SC_OPEN_MAX')
except ValueError:
    MAXFD = 256


def _close_fds():
    for i in range(3, MAXFD):
        try:
            os.close(i)
        # pylint: disable=W0704
        except Exception:
            pass


def create_activity_id():
    """Generate a new, unique ID for this activity"""
    return util.unique_id()


def _mkdir(path):
    try:
        os.mkdir(path)
    except OSError as e:
        if e.errno != EEXIST:
            raise e


def get_environment(activity):
    environ = os.environ.copy()

    bin_path = os.path.join(activity.get_path(), 'bin')

    activity_root = env.get_profile_path(activity.get_bundle_id())
    _mkdir(activity_root)

    instance_dir = os.path.join(activity_root, 'instance')
    _mkdir(instance_dir)

    data_dir = os.path.join(activity_root, 'data')
    _mkdir(data_dir)

    tmp_dir = os.path.join(activity_root, 'tmp')
    _mkdir(tmp_dir)

    environ['SUGAR_BUNDLE_PATH'] = activity.get_path()
    environ['SUGAR_BUNDLE_ID'] = activity.get_bundle_id()
    environ['SUGAR_ACTIVITY_ROOT'] = activity_root
    environ['PATH'] = bin_path + ':' + environ['PATH']

    if activity.get_path().startswith(env.get_user_activities_path()):
        environ['SUGAR_LOCALEDIR'] = os.path.join(activity.get_path(),
                                                  'locale')

    return environ


def get_command(activity, activity_id=None, object_id=None, uri=None,
                activity_invite=False):
    if not activity_id:
        activity_id = create_activity_id()

    command = activity.get_command().split(' ')
    command.extend(['-b', activity.get_bundle_id()])
    command.extend(['-a', activity_id])

    if object_id is not None:
        command.extend(['-o', object_id])
    if uri is not None:
        command.extend(['-u', uri])
    if activity_invite:
        command.append('-i')

    # if the command is in $BUNDLE_ROOT/bin, execute the absolute path so there
    # is no need to mangle with the shell's PATH
    if '/' not in command[0]:
        bin_path = os.path.join(activity.get_path(), 'bin')
        absolute_path = os.path.join(bin_path, command[0])
        if os.path.exists(absolute_path):
            command[0] = absolute_path

    logging.debug('launching: %r' % command)

    return command


def open_log_file(activity):
    i = 1
    while True:
        path = env.get_logs_path('%s-%s.log' % (activity.get_bundle_id(), i))
        try:
            fd = os.open(path, os.O_EXCL | os.O_CREAT | os.O_WRONLY, 0o644)
            f = os.fdopen(fd, 'w')
            return (path, f)
        except OSError as e:
            if e.errno == EEXIST:
                i += 1
            elif e.errno == ENOSPC:
                # not the end of the world; let's try to keep going.
                return (os.devnull, open(os.devnull, 'w'))
            else:
                raise e


class ActivityCreationHandler(GObject.GObject):
    """Sugar-side activity creation interface

    This object uses a dbus method on the ActivityFactory
    service to create the new activity.  It generates
    GObject events in response to the success/failure of
    activity startup using callbacks to the service's
    create call.
    """

    def __init__(self, bundle, handle):
        """Initialise the handler

        bundle -- the ActivityBundle to launch
        activity_handle -- stores the values which are to
            be passed to the service to uniquely identify
            the activity to be created and the sharing
            service that may or may not be connected with it

            sugar4.activity.activityhandle.ActivityHandle instance

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
        super().__init__()

        self._bundle = bundle
        self._service_name = bundle.get_bundle_id()
        self._handle = handle

        bus = dbus.SessionBus()
        bus_object = bus.get_object(_SHELL_SERVICE, _SHELL_PATH)
        self._shell = dbus.Interface(bus_object, _SHELL_IFACE)

        if handle.activity_id is not None and handle.object_id is None:
            datastore.find({'activity_id': self._handle.activity_id},
                           reply_handler=self._find_object_reply_handler,
                           error_handler=self._find_object_error_handler)
        else:
            self._launch_activity()

    def _launch_activity(self):
        if self._handle.activity_id is not None:
            self._shell.ActivateActivity(
                self._handle.activity_id,
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

        environ = get_environment(self._bundle)
        (log_path, log_file) = open_log_file(self._bundle)
        command = get_command(self._bundle, self._handle.activity_id,
                              self._handle.object_id, self._handle.uri,
                              self._handle.invited)

        dev_null = open(os.devnull, 'r')
        
        from jarabe.model import shell
        model = shell.get_model()
        pass_fds = ()
        if hasattr(model, 'compositor') and model.compositor is not None:
            fd = model.compositor.get_client_socket_fd()
            environ['WAYLAND_SOCKET'] = str(fd)
            environ['WAYLAND_DISPLAY'] = os.environ.get('WAYLAND_DISPLAY', 'wayland-0')
            environ['GDK_BACKEND'] = 'wayland'
            pass_fds = (fd,)
            
        kwargs = {
            'env': environ,
            'cwd': str(self._bundle.get_path()),
            'stdin': dev_null.fileno(),
            'stdout': log_file.fileno(),
            'stderr': log_file.fileno()
        }
        
        if os.name != 'nt' and pass_fds:
            kwargs['pass_fds'] = pass_fds

        child = subprocess.Popen([str(s) for s in command], **kwargs)

        GLib.child_watch_add(GLib.PRIORITY_DEFAULT, child.pid,
                             _child_watch_cb,
                             (log_file, self._handle.activity_id))

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
        logging.error('Activity activation request failed %s' % err)

    def _create_reply_handler(self):
        logging.debug('Activity created %s (%s).' %
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
                logging.debug('Multiple objects has the same activity_id.')
            self._handle.object_id = jobjects[0]['uid']
        self._launch_activity()

    def _find_object_error_handler(self, err):
        logging.error('Datastore find failed %s' % err)
        self._launch_activity()


def create(bundle, activity_handle=None):
    """Create a new activity from its name."""
    if not activity_handle:
        activity_handle = ActivityHandle()
    return ActivityCreationHandler(bundle, activity_handle)


def create_with_uri(bundle, uri):
    """Create a new activity and pass the uri as handle."""
    activity_handle = ActivityHandle(uri=uri)
    return ActivityCreationHandler(bundle, activity_handle)


def create_with_object_id(bundle, object_id):
    """Create a new activity and pass the object id as handle."""
    activity_handle = ActivityHandle(object_id=object_id)
    return ActivityCreationHandler(bundle, activity_handle)


def _child_watch_cb(pid, condition, user_data):
    log_file, activity_id = user_data

    if os.WIFEXITED(condition):
        status = os.WEXITSTATUS(condition)
        signum = None
        if status == 0:
            message = 'Normal successful completion'
        else:
            message = 'Exited with status %s' % status
    elif os.WIFSIGNALED(condition):
        status = None
        signum = os.WTERMSIG(condition)
        message = 'Terminated by signal %s' % signum
    else:
        status = None
        signum = os.WTERMSIG(condition)
        message = 'Undefined status with signal %s' % signum

    try:
        log_file.write(
            '%s, pid %s activity_id %s\n' % (message, pid, activity_id))
    finally:
        log_file.close()

    # try to reap zombies in case SIGCHLD has not been set to SIG_IGN
    try:
        os.waitpid(pid, 0)
    except OSError:
        # SIGCHLD = SIG_IGN, no zombies
        pass

    if status or signum:
        # XXX have to recreate dbus object since we can't reuse
        # ActivityCreationHandler's one, see
        # https://bugs.freedesktop.org/show_bug.cgi?id=23507
        bus = dbus.SessionBus()
        bus_object = bus.get_object(_SHELL_SERVICE, _SHELL_PATH)
        shell = dbus.Interface(bus_object, _SHELL_IFACE)

        def reply_handler_cb(*args):
            pass

        def error_handler_cb(error):
            logging.error('Cannot send NotifyLaunchFailure to the shell')

        # TODO send launching failure but activity could already show
        # main window, see http://bugs.sugarlabs.org/ticket/1447#comment:19
        shell.NotifyLaunchFailure(activity_id,
                                  reply_handler=reply_handler_cb,
                                  error_handler=error_handler_cb)
