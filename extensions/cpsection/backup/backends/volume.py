# Copyright (C) 2013, Martin Abente Lahaye - tch@sugarlabs.org
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
import shutil
import statvfs
import tarfile
import logging
from datetime import datetime

from gettext import gettext as _
from gi.repository import Gio
from gi.repository import GObject

from sugar3 import env
from sugar3 import profile
from jarabe.journal import model

from backend_tools import Backend, PreConditionsError, PreConditionsChoose
from backend_tools import get_valid_file_name

DIR_SIZE = 4096
DS_SOURCE_NAME = 'datastore'
SN_PATH_X86 = '/ofw/serial-number/serial-number'
SN_PATH_ARM = '/proc/device-tree/serial-number'


class Backup(Backend):

    BACKUP_NAME = '%s_%s.xob'

    def __init__(self):
        Backend.__init__(self)
        self._volume = None
        self._percent = 0

    def _set_volume(self, option):
        if self._volume is not None:
            return

        if option is not None and 'volume' in option:
            self._volume = option['volume']
            return

        volume_options = _get_volume_options()
        logging.error('volume_options %s', volume_options)
        if not volume_options['options']:
            raise PreConditionsError(_('Please connect a device to continue'))

        volume = _value_if_one_option(volume_options)

        if volume is not None:
            self._volume = volume
            return

        raise PreConditionsChoose(_('Select your volume'), volume_options)

    def verify_preconditions(self, option=None):
        """
        option: dictionary
        """
        self._set_volume(option)
        self._uncompressed_size = _get_datastore_size()
        if _get_volume_space(self._volume) < self._uncompressed_size:
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
        backup_file_name = self.BACKUP_NAME % (
            _get_identifier(), datetime.now().strftime('%Y%m%d'))
        backup_file_name = get_valid_file_name(backup_file_name)
        return os.path.join(self._volume, backup_file_name)

    def _do_continue(self):
        self._tarfile.add(self._entries.pop())
        percent = int((1.0 - float(len(self._entries)) / self._total) * 100)
        if percent != self._percent:
            self._percent = percent
            logging.debug('backup-local progress is %f', percent)
            self.emit('progress', float(percent) / 100.0)

        if self._cancelled:
            self._do_cancel()
        elif len(self._entries) == 0:
            self._do_finish()
        else:
            GObject.idle_add(self._do_continue)

    def _do_cancel(self):
        self._tarfile.close()
        logging.debug('Cancel backup operation, remove file %s',
                      self._checkpoint)
        os.remove(self._checkpoint)
        self.emit('cancelled')

    def _do_finish(self):
        self._tarfile.close()
        # Add metadata to the file created
        metadata = model.get(self._checkpoint)
        metadata['description'] = _('Backup from user %s') % \
            profile.get_nick_name()
        metadata['icon_color'] = profile.get_color().to_string()
        metadata['uncompressed_size'] = self._uncompressed_size
        metadata['mime_type'] = 'application/vnd.olpc-journal-backup'
        model.write(metadata, self._checkpoint)
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
        self._percent = 0
        self._cancellable = True

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

        volume_options = _get_volume_options()
        logging.error('volume_options %s', volume_options)
        if not volume_options['options']:
            raise PreConditionsError(_('Please connect a device to continue'))

        volume = _value_if_one_option(volume_options)
        if volume is not None:
            self._volume = volume
            return

        raise PreConditionsChoose(_('Select your volume'), volume_options)

    def _set_checkpoint(self, option):
        if self._checkpoint is not None:
            return

        if option is not None and 'checkpoint' in option:
            self._checkpoint = option['checkpoint']
            return

        checkpoint_options = _get_checkpoint_options(self._volume)

        if not checkpoint_options['options']:
            raise PreConditionsError(_('No checkpoints found in the device'))

        checkpoint = _value_if_one_option(checkpoint_options)

        if checkpoint is not None:
            self._checkpoint = checkpoint
            return

        raise PreConditionsChoose(_('Select your checkpoint'),
                                  checkpoint_options)

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
            self._tarfile.extract(tarinfo, path='/')
            self._bytes += DIR_SIZE if tarinfo.isdir() else tarinfo.size
            percent = int(self._bytes / self._checkpoint_size * 100)
            if percent != self._percent:
                self._percent = percent
                logging.debug('restore-local progress is %f', percent)
                self.emit('progress', float(percent) / 100.0)
            GObject.idle_add(self._do_continue)
        else:
            self._do_finish()

    def _do_finish(self):
        self._tarfile.close()
        self._cancellable = True
        self.emit('finished')

    def start(self):
        self._cancellable = False
        self.emit('started')
        logging.debug('Starting with checkpoint %s', self._checkpoint)
        self._tarfile = tarfile.open(self._checkpoint, 'r:gz')
        self._bytes = 0.0
        self._reset_datastore()
        GObject.idle_add(self._do_continue)

    def cancel(self):
        if not self._cancellable:
            # restore can't be interrupted
            raise Exception()


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
    # read information in the metadata
    metadata = model.get(path)
    if 'uncompressed_size' in metadata:
        size = int(metadata['uncompressed_size'])
        logging.error('size from metadata = %d', size)
    else:
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
    return profile.get_nick_name()


def _get_datastore_path():
    return os.path.join(env.get_profile_path(), DS_SOURCE_NAME)


def _value_if_one_option(options):
    if len(options['options']) == 1:
        return options['options'][0]['value']
    return None


def _get_checkpoint_options(volume):
    options = {}
    options['parameter'] = 'checkpoint'
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
    options['options'] = []

    for mount in Gio.VolumeMonitor.get().get_mounts():
        option = {}
        option['description'] = mount.get_name()
        option['value'] = mount.get_root().get_path()
        options['options'].append(option)

    return options


def get_name():
    return _('Local Device Backup')


def get_backup():
    return Backup()


def get_restore():
    return Restore()
