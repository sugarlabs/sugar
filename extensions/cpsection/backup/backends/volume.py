# Copyright (C) 2013, Martin Abente Lahaye - tch@sugarlabs.org
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

import os
import shutil
import statvfs
import tarfile
import logging
from datetime import datetime

from gettext import gettext as _
from gi.repository import Gio
from gi.repository import GObject

from sugar import env


DIR_SIZE = 4096
DS_SOURCE_NAME = 'datastore'
SN_PATH_X86 = '/ofw/serial-number/serial-number'
SN_PATH_ARM = '/proc/device-tree/serial-number'


class PreConditionsError(Exception):
    pass


class PreConditionsChoose(Exception):

    def __init__(self, message, options):
        Exception.__init__(self, message)
        self.options = options


class Backend(GObject.GObject):

    __gsignals__ = {
        'started':   (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'progress':  (GObject.SignalFlags.RUN_FIRST, None, ([float])),
        'finished':  (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'cancelled': (GObject.SignalFlags.RUN_FIRST, None, ([]))}

    def verify_preconditions(self):
        raise NotImplementedError()

    def start(self):
        raise NotImplementedError()

    def cancel(self):
        raise NotImplementedError()


class Backup(Backend):

    BACKUP_NAME = '%s.xob'

    def __init__(self):
        Backend.__init__(self)
        self._volume = None

    def _set_volume(self, option):
        if self._volume is not None:
            return

        if option is not None and 'volume' in option:
            self._volume = option['volume']
            return

        options = _get_volume_options()
        volume = _value_if_one_option(options)
        if volume is not None:
            self._volume = volume
            return

        raise PreConditionsChoose(_('Select your volume'), options)

    def verify_preconditions(self, option=None):
        self._set_volume(option)
        if _get_volume_space(self._volume) < _get_datastore_size():
            raise PreConditionsError(_('Not enough space in volume'))

    def _get_datastore_entries(self):
        ''' gathers datastore top level directories only '''
        ds_path = _get_datastore_path()
        entries = []
        for item in os.listdir(ds_path):
            entry = os.path.join(ds_path, item)
            if os.path.isdir(entry):
                entries.append(entry)
        return entries

    def _generate_checkpoint(self):
        return os.path.join(self._volume, self.BACKUP_NAME %
                           (datetime.now().strftime('%Y%m%d')))

    def _do_continue(self):
        self._tarfile.add(self._entries.pop())
        percent = (1.0 - float(len(self._entries)) / self._total) * 100
        logging.debug('backup-local progress is %d', percent)
        self.emit('progress', percent)

        if self._cancelled:
            self._do_cancel()
        elif len(self._entries) == 0:
            self._do_finish()
        else:
            GObject.idle_add(self._do_continue)

    def _do_cancel(self):
        self._tarfile.close()
        os.remove(self._checkpoint)
        self.emit('cancelled')

    def _do_finish(self):
        self._tarfile.close()
        self.emit('finished')

    def start(self):
        self.emit('started')
        self._checkpoint = self._generate_checkpoint()
        self._tarfile = tarfile.open(self._checkpoint, 'w:gz')
        self._entries = self._get_datastore_entries()
        self._total = len(self._entries)
        self._cancelled = False
        GObject.idle_add(self._do_continue)

    def cancel(self):
        self._cancelled = True


class Restore(Backend):

    def __init__(self):
        Backend.__init__(self)
        self._volume = None
        self._checkpoint = None
        self._checkpoint_size = None

    def _reset_datastore(self):
        ''' erase all contents from current datastore '''
        datastore_path = _get_datastore_path()
        if os.path.exists(datastore_path):
            shutil.rmtree(datastore_path)
        os.makedirs(datastore_path)

    def _set_volume(self, option):
        if self._volume is not None:
            return

        if option is not None and 'volume' in option:
            self._volume = option['volume']
            return

        options = _get_volume_options()
        volume = _value_if_one_option(options)
        if volume is not None:
            self._volume = volume
            return

        raise PreConditionsChoose(_('Select your volume'), options)

    def _set_checkpoint(self, option):
        if self._checkpoint is not None:
            return

        if option is not None and 'checkpoint' in option:
            self._checkpoint = option['checkpoint']
            return

        options = _get_checkpoint_options(self._volume)
        checkpoint = _value_if_one_option(options)
        if checkpoint is not None:
            self._checkpoint = checkpoint
            return

        raise PreConditionsChoose(_('Select your checkpoint'), options)

    def _set_checkpoint_size(self):
        self._checkpoint_size = _get_checkpoint_size(self._checkpoint)

    def verify_preconditions(self, option=None):
        self._set_volume(option)
        self._set_checkpoint(option)
        self._set_checkpoint_size()
        if _get_volume_space(env.get_profile_path()) < self._checkpoint_size:
            raise PreConditionsError(_('Not enough space in disk'))

    def _do_continue(self):
        tarinfo = self._tarfile.next()
        if tarinfo is not None:
            self._tarfile.extract(tarinfo)
            self._bytes += DIR_SIZE if tarinfo.isdir() else tarinfo.size
            percent = self._bytes / self._checkpoint_size * 100
            logging.debug('restore-local progress is %d', percent)
            self.emit('progress', percent)
            GObject.idle_add(self._do_continue)
        else:
            self._do_finish()

    def _do_finish(self):
        self._tarfile.close()
        self.emit('finished')

    def start(self):
        self.emit('started')
        self._tarfile = tarfile.open(self._checkpoint, 'r:gz')
        self._bytes = 0.0
        self._reset_datastore()
        GObject.idle_add(self._do_continue)


def _get_volume_space(path):
    stat = os.statvfs(path)
    return stat[statvfs.F_BSIZE] * stat[statvfs.F_BAVAIL]


def _get_datastore_size():
    # XXX: is there a better way?
    size = 0
    for root, dirnames, filenames in os.walk(_get_datastore_path()):
        for d in dirnames:
            size += os.path.getsize(os.path.join(root, d))
        for f in filenames:
            size += os.path.getsize(os.path.join(root, f))
    return size


def _get_checkpoint_size(path):
    size = 0
    with tarfile.open(path, 'r:gz') as file:
        for tarinfo in file:
            size += DIR_SIZE if tarinfo.isdir() else tarinfo.size
    return size


def _get_identifier():
    path = None
    if os.path.exists(SN_PATH_X86):
        path = SN_PATH_X86
    elif os.path.exists(SN_PATH_ARM):
        path = SN_PATH_ARM
    if path is not None:
        with open(path, 'r') as file:
            return file.read().rstrip('\0\n')
    return 'user'


def _get_datastore_path():
    return os.path.join(env.get_profile_path(), DS_SOURCE_NAME)


def _value_if_one_option(options):
    if len(options['options']) == 1:
        return options['options'][0]['value']
    return None


def _get_checkpoint_options(volume):
    options = {}
    options['parameter'] = 'checkpoint'
    options['message'] = _('Select your restore check point')
    options['options'] = []

    for checkpoint in os.listdir(volume):
        if not checkpoint.endswith('.xob'):
            continue
        option = {}
        option['description'] = checkpoint
        option['value'] = os.path.join(volume, checkpoint)
        options['options'].append(option)

    return options


def _get_volume_options():
    options = {}
    options['parameter'] = 'volume'
    options['message'] = _('Select your device')
    options['options'] = []

    for mount in Gio.VolumeMonitor.get().get_mounts():
        option = {}
        option['description'] = mount.get_name()
        option['value'] = mount.get_root().get_path()
        options['options'].append(option)

    return options


def get_name():
    return _('Local Backup')


def get_backup():
    return Backup


def get_restore():
    return Restore
