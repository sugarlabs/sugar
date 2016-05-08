from dbus.mainloop.glib import DBusGMainLoop
from sugar3.datastore import datastore
from sugar3 import env
import json
import subprocess
import os
import urllib2

DBusGMainLoop(set_as_default=True)


class RemoteJournal(object):
    def __init__(self):
        self.runSync()

    def runSync(self):
        query = {}
        ds_objects, num_objects = datastore.find(query)
        upload_to_server = []
        download_from_server = []
        for ds_object in ds_objects:
            bool_keep = False
            bool_remote = False
            try:
                bool_keep = ((ds_object.metadata['keep'] == '1') or
                             (ds_object.metadata['title_set_by_user'] != '0'))
                bool_remote = (ds_object.metadata['remote'] == '1')
            except:
                pass

            if bool_keep and bool_remote:
                download_from_server.append(ds_object)
            elif not (bool_keep or bool_remote):
                upload_to_server.append(ds_object)

        if upload_to_server:
            self._bulk_rsync_to_server(upload_to_server)

        if download_from_server:
            self._bulk_rsync_from_server(download_from_server)

    def _check_server_available(self, server):
        try:
            urllib2.urlopen(server).read()
            return True
        except (urllib2.HTTPError, urllib2.URLError):
            return False

    def _delete_files_from_dir(self, dir_path):
        for temp_file in os.listdir(dir_path):
            file_path = os.path.join(dir_path, temp_file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except:
                pass

    def _get_identifier(self, identifier):
        path = os.path.join(env.get_profile_path(), 'identifiers', identifier)
        data = ""
        if os.path.exists(path):
            fh = open(path, 'r')
            data = fh.read().rstrip('\0\n')
            fh.close()
        return data

    def _get_sn(self):
        path = os.path.join('/ofw', 'mfg-data/SN')
        if os.path.exists(path):
            fh = open(path, 'r')
            data = fh.read().rstrip('\0\n')
            fh.close()
            return data

        path = os.path.join(env.get_profile_path(), 'identifiers/sn')
        if os.path.exists(path):
            fh = open(path, 'r')
            data = fh.read().rstrip('\0\n')
            fh.close()
            return data

        return 'SHF00000000'

    def _bulk_rsync_to_server(self, ds_objects):
        # Create temp files
        temp_journal_path = os.path.join(env.get_profile_path(),
                                         'journal-backups')
        if not os.path.exists(temp_journal_path):
            os.makedirs(temp_journal_path)
        self._delete_files_from_dir(temp_journal_path)
        for ds_object in ds_objects:
            ds_object_metadata = {}
            for key in ds_object.metadata.keys():
                if not key == 'preview':
                    try:
                        ds_object_metadata[key] = ds_object.metadata[key]
                    except:
                        pass
            file_path = os.path.join(temp_journal_path,
                                     os.path.basename(ds_object.get_file_path()) +
                                     ".metadata")
            fh = open(file_path, 'w+')
            fh.write(json.dumps(ds_object_metadata))
            fh.close()
            ds_object.metadata['remote'] = '1'
            ds_object.file_path = None
            datastore.write(ds_object)

        # Upload to server
        backup_url = self._get_identifier('backup_url')
        server_address = "http://" + backup_url
        if self._check_server_available(server_address):
            sn = self._get_sn()
            pk_path = os.path.join(env.get_profile_path(), 'owner.key')
            from_path = temp_journal_path
            to_path = backup_url + ":"

            ssh_cmd = '/usr/bin/ssh -F /dev/null -o "PasswordAuthentication no"\
                -o "StrictHostKeyChecking no" -o "PubkeyAcceptedKeyTypes ssh-dss"\
                -i %s -l %s' % (pk_path, sn)

            rsync_cmd = ['rsync', '-zrl', '--checksum', '--partial', '--timeout=160',
                         '-e', ssh_cmd, from_path, to_path]

            rsync_exit = subprocess.call(rsync_cmd)

            if rsync_exit != 0:
                print "Error"
            else:
                print "Done"
                self._delete_files_from_dir(temp_journal_path)

    def _bulk_rsync_from_server(self, ds_objects):
        # Download from server
        temp_journal_path = os.path.join(env.get_profile_path(),
                                         'journal-backups')
        backup_url = self._get_identifier('backup_url')
        server_address = "http://" + backup_url
        if self._check_server_available(server_address):
            sn = self._get_sn()
            pk_path = os.path.join(env.get_profile_path(), 'owner.key')
            to_path = temp_journal_path + '/'

            for ds_object in ds_objects:
                file_name = ds_object.metadata['activity_id'] + '.metadata'
                from_path = backup_url + ":journal-backups/" + file_name

                ssh_cmd = '/usr/bin/ssh -F /dev/null -o "PasswordAuthentication no"\
                    -o "StrictHostKeyChecking no" -o "PubkeyAcceptedKeyTypes ssh-dss"\
                    -i %s -l %s' % (pk_path, sn)

                rsync_cmd = ['rsync', '-zrl', '--checksum', '--partial', '--timeout=160',
                             '-e', ssh_cmd, from_path, to_path]

                rsync_exit = subprocess.call(rsync_cmd)

                if rsync_exit != 0:
                    print "Error2"
                else:
                    print "Done2"
                    datastore.delete(ds_object.object_id)
                    fh = open(os.path.join(to_path, file_name), 'r')
                    ds_object_metadata = json.loads(fh.read())
                    fh.close()
                    ds_object = datastore.create()
                    for key in ds_object_metadata.keys():
                        ds_object.metadata[key] = ds_object_metadata[key]
                    ds_object.metadata['keep'] = '1'
                    ds_object.metadata['remote'] = '0'
                    datastore.write(ds_object)
        self._delete_files_from_dir(temp_journal_path)


# For launch from terminal
Instance = RemoteJournal()