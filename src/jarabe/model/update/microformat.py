# Copyright (C) 2008-2013 One Laptop per Child
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


"""
Activity information microformat parser.

This updater backend pulls activity information from a HTML page that
embeds activity information in special CSS selectors. For more info, see
http://wiki.sugarlabs.org/go/Activity_Team/Activity_Microformat
"""

import os
import locale
import logging
from tempfile import NamedTemporaryFile

from StringIO import StringIO
from ConfigParser import ConfigParser
from zipfile import ZipFile
from urlparse import urljoin
from HTMLParser import HTMLParser

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gio

from sugar3.bundle.bundleversion import NormalizedVersion, InvalidVersionError

from jarabe.util import httprange
from jarabe.model import bundleregistry
from jarabe.model.update import BundleUpdate
from jarabe.util.downloader import Downloader

_logger = logging.getLogger('microformat')
_MICROFORMAT_URL_PATH = 'org.sugarlabs.update'
_MICROFORMAT_URL_KEY = 'microformat-update-url'


class _UpdateHTMLParser(HTMLParser):
    """HTML parser to pull out data expressed in our microformat."""

    def __init__(self, base_href):
        HTMLParser.__init__(self)
        self.base_href = base_href
        self.results = {}
        self.group_name = self.group_desc = None
        self.in_group_name = self.in_group_desc = self.in_activity = 0
        self._clear_info()

    def _clear_info(self):
        self.in_activity_id = self.in_activity_url = 0
        self.in_activity_version = 0
        self.in_activity_optional = 0
        self.last_id = self.last_version = self.last_url = None
        self.last_optional = False

    def handle_starttag(self, tag, attrs):
        classes = ' '.join([val for attr, val in attrs if attr == 'class'])\
                  .split()
        if self.in_group_name == 0:
            if ('id', 'olpc-activity-group-name') in attrs:
                self.in_group_name = 1
        else:
            self.in_group_name += 1

        if self.in_group_desc == 0:
            if ('id', 'olpc-activity-group-desc') in attrs:
                self.in_group_desc = 1
        else:
            self.in_group_desc += 1

        if self.in_activity == 0:
            if 'olpc-activity-info' in classes:
                self.in_activity = 1
                self._clear_info()
            return

        self.in_activity += 1
        if self.in_activity_id == 0:
            if 'olpc-activity-id' in classes:
                self.in_activity_id = 1
        else:
            self.in_activity_id += 1

        if self.in_activity_version == 0:
            if 'olpc-activity-version' in classes:
                self.in_activity_version = 1
        else:
            self.in_activity_version += 1

        if self.in_activity_url == 0:
            if 'olpc-activity-url' in classes:
                self.in_activity_url = 1
        else:
            self.in_activity_url += 1

        if self.in_activity_optional == 0:
            if 'olpc-activity-optional' in classes:
                self.in_activity_optional = 1
        else:
            self.in_activity_optional += 1

        # an href inside activity_url is the droid we are looking for.
        if self.in_activity_url > 0:
            for a, v in attrs:
                if a == 'href':
                    self.last_url = urljoin(self.base_href, v)
                    break

    def handle_data(self, data):
        if self.in_group_name:
            self.group_name = data.strip()

        if self.in_group_desc:
            self.group_desc = data.strip()

        if self.in_activity_id > 0:
            if self.last_id is None:
                self.last_id = data.strip()
            else:
                self.last_id = self.last_id + data.strip()

        if self.in_activity_version > 0:
            try:
                self.last_version = NormalizedVersion(data.strip())
            except InvalidVersionError:
                pass

        if self.in_activity_optional > 0:
            # a value 1 means that this activity is optional
            self.last_optional = data.strip() == '1'

    def handle_endtag(self, tag):
        if self.in_group_name > 0:
            self.in_group_name -= 1

        if self.in_group_desc > 0:
            self.in_group_desc -= 1

        if self.in_activity_id > 0:
            self.in_activity_id -= 1

        if self.in_activity_version > 0:
            self.in_activity_version -= 1

        if self.in_activity_optional > 0:
            self.in_activity_optional -= 1

        if self.in_activity_url > 0:
            self.in_activity_url -= 1

        if self.in_activity > 0:
            self.in_activity -= 1

            if self.in_activity == 0:
                self._process_result()

    def _process_result(self):
        if self.last_id is None or self.last_id.strip() == '':
            return

        if self.last_version is not None and self.last_url is not None:
            if self.last_id in self.results:
                if self.last_version < self.results[self.last_id][0]:
                    return  # already found a better version
            self.results[self.last_id] = (self.last_version, self.last_url,
                                          self.last_optional)


class MicroformatUpdater(object):
    """
    Microformat updater backend. The rough code flow here is:
     1. Query update URL and parse results
     2. For each activity update:
       a) If we already have this activity installed, use GIO to asynchronously
          lookup the size of the download.
       b) If we don't have the activity installed, use MetadataLookup
          to lookup activity name and size.
    """
    def __init__(self):
        self._icon_temp_files = []

    def _query(self):
        self.clean()
        settings = Gio.Settings(_MICROFORMAT_URL_PATH)
        url = settings.get_string(_MICROFORMAT_URL_KEY)
        _logger.debug("Query %s %r", url, url)
        if url == "":
            self._completion_cb([])
            return

        self._parser = _UpdateHTMLParser(url)
        # wiki.laptop.org have agresive cache, we set max-age=600
        # to be sure the page is no older than 10 minutes
        request_headers = {'Cache-Control': 'max-age=600'}
        downloader = Downloader(url, request_headers=request_headers)
        downloader.connect('got-chunk', self._got_chunk_cb)
        downloader.connect('complete', self._complete_cb)
        downloader.download_chunked()
        self._progress_cb(None, 0)

    def _got_chunk_cb(self, downloader, data):
        self._parser.feed(data.get_data())

    def _complete_cb(self, downloader, result):
        if isinstance(result, Exception):
            _logger.warning("Failed to read update info: %s", result)
            self._error_cb(result)
            return

        self._parser.close()
        _logger.debug("Found %d activities", len(self._parser.results))
        self._filter_results()
        self._check_next_update()

    def _filter_results(self):
        # Remove updates for which we already have an equivalent or newer
        # version installed. Queue the remaining ones to be checked.
        registry = bundleregistry.get_registry()
        self._bundles_to_check = []
        for bundle_id, data in self._parser.results.iteritems():
            # filter optional activities for automatic updates
            if self._auto and data[2] is True:
                logging.debug('filtered optional activity %s', bundle_id)
                continue

            bundle = registry.get_bundle(bundle_id)
            if bundle:
                if data[0] <= NormalizedVersion(bundle.get_activity_version()):
                    continue

            name = bundle.get_name() if bundle else None
            bundle_update = BundleUpdate(bundle_id, name, data[0], data[1], 0,
                                         optional=data[2])
            self._bundles_to_check.append(bundle_update)
        self._total_bundles_to_check = len(self._bundles_to_check)
        _logger.debug("%d results after filter", self._total_bundles_to_check)

    def _check_next_update(self):
        if self._cancelling or len(self._bundles_to_check) == 0:
            self._completion_cb(self._updates)
            return

        total = self._total_bundles_to_check
        current = total - len(self._bundles_to_check)
        progress = current / float(total)

        self._bundle_update = self._bundles_to_check.pop()
        _logger.debug("Check %s", self._bundle_update.bundle_id)

        # There is no need for a special name lookup for an automatic update.
        # The name lookup is only for UI purposes, but we are running in the
        # background.
        if self._bundle_update.name is None and self._auto:
            self._bundle_update.name = self._bundle_update.bundle_id

        if self._bundle_update.name is not None:
            # if we know the name, we just perform an asynchronous size check
            _logger.debug("Performing async size lookup")
            size_check = Downloader(self._bundle_update.link)
            size_check.connect('complete', self._size_lookup_cb)
            size_check.get_size()
            self._progress_cb(self._bundle_update.name, progress)
        else:
            # if we don't know the name, we run a metadata lookup and get
            # the size and name that way
            _logger.debug("Performing metadata lookup")
            namelookup = MetadataLookup(self._bundle_update.link)
            namelookup.connect('complete', self._name_lookup_complete)
            namelookup.run()
            self._progress_cb(self._bundle_update.bundle_id, progress)

    def _size_lookup_cb(self, downloader, result):
        if isinstance(result, Exception):
            _logger.warning("Failed to perform size lookup: %s", result)
        else:
            self._bundle_update.size = result
            self._updates.append(self._bundle_update)

        GLib.idle_add(self._check_next_update)

    def _name_lookup_complete(self, lookup, result, size, icon_file_name):
        _logger.debug("Name lookup result: %r", result)
        if icon_file_name is not None:
            self._icon_temp_files.append(icon_file_name)
            logging.debug('Adding temporary file %s to list', icon_file_name)

        if size is None:
            # if the size lookup failed, assume this update is bad
            self._check_next_update()
            return

        if result is None or isinstance(result, Exception):
            # if we failed to find the name, add the update anyway, using the
            # bundle_id as the best name we have
            self._bundle_update.name = self._bundle_update.bundle_id
        else:
            self._bundle_update.name = result

        self._bundle_update.size = size
        if icon_file_name is not None:
            self._bundle_update.icon_file_name = icon_file_name

        self._updates.append(self._bundle_update)
        self._check_next_update()

    def fetch_update_info(self, installed_bundles, auto, progress_cb,
                          completion_cb, error_cb):
        self._completion_cb = completion_cb
        self._progress_cb = progress_cb
        self._error_cb = error_cb
        self._cancelling = False
        self._updates = []
        self._bundles_to_check = []
        self._total_bundles_to_check = 0
        self._auto = auto
        self._query()

    def cancel(self):
        self._cancelling = True

    def clean(self):
        for filename in self._icon_temp_files:
            logging.debug('Removing temporary file %s', filename)
            try:
                os.unlink(filename)
            except OSError:
                pass
        self._icon_temp_files = []


class MetadataLookup(GObject.GObject):
    """
    Look up the localized activity name and size of a bundle.

    This is useful when no previous version of the activity is installed,
    and there is no local source of the activity's name.
    """
    __gsignals__ = {
        'complete': (GObject.SignalFlags.RUN_FIRST,
                     None, (object, object, object)),
    }

    def __init__(self, url):
        GObject.GObject.__init__(self)
        self._url = url
        self._icon_file_name = None
        self._size = None

    def run(self):
        # Perform the name lookup, catch any exceptions, and report the result.
        try:
            name = self._do_name_lookup()
            self._complete(name)
        except Exception, e:
            self._complete(e)

    def _do_name_lookup(self):
        fd = httprange.open(self._url)
        self._size = fd.size()
        return self._name_from_fd(fd)

    def _name_from_fd(self, fd):
        self._zf = ZipFile(fd)
        self._namelist = self._zf.namelist()
        self._prefix = None
        have_activity_info = False
        have_library_info = False
        for path in self._namelist:
            if path.count('/') != 2:
                continue
            if path.endswith('/activity/activity.info'):
                have_activity_info = True
                self._prefix = path.split('/', 1)[0]
                break
            if path.endswith('/library/library.info'):
                have_library_info = True
                self._prefix = path.split('/', 1)[0]
                break

        if self._prefix is None:
            raise Exception("Couldn't find activity prefix")

        # To find the localized name, we first look for an activity.linfo file
        # in the current locale.
        # We fall back on pulling the non-localized name from activity.info,
        # if there is one.
        # The final fallback is pulling the name from library.info; in the
        # case of a content bundle, that name is expected to be already
        # localized according to the content.
        name = self._locale_data_lookup()
        icon_path = None
        if not name and have_activity_info:
            name = self._activity_info_lookup('name')
        if not name and have_library_info:
            name = self._library_info_lookup('name')

        # get icondata
        if have_activity_info:
            icon_name = self._activity_info_lookup('icon')
        if not name and have_library_info:
            icon_name = self._library_info_lookup('icon')
        icon_path = os.path.join(self._prefix, 'activity',
                                 '%s.svg' % icon_name)
        if icon_path is not None and icon_path in self._namelist:
            icon_data = self._zf.read(icon_path)
            # save the icon to a temporary file
            with NamedTemporaryFile(mode='w', suffix='.svg',
                                    delete=False) as iconfile:
                iconfile.write(icon_data)
                self._icon_file_name = iconfile.name
        return name

    def _locale_data_lookup(self):
        lang = locale.getdefaultlocale()[0]
        if lang is None:
            return None

        for f in ('locale/%s/activity.linfo' % lang,
                  'locale/%s/activity.linfo' % lang[:2]):
            filename = os.path.join(self._prefix, f)
            if filename not in self._namelist:
                continue
            cp = ConfigParser()
            cp.readfp(StringIO(self._zf.read(filename)))
            return cp.get('Activity', 'name')
        return None

    def _activity_info_lookup(self, parameter):
        filename = os.path.join(self._prefix, 'activity', 'activity.info')
        cp = ConfigParser()
        cp.readfp(StringIO(self._zf.read(filename)))
        if cp.has_option('Activity', parameter):
            return cp.get('Activity', parameter)
        else:
            return ''

    def _library_info_lookup(self, parameter):
        filename = os.path.join(self._prefix, 'library', 'library.info')
        cp = ConfigParser()
        cp.readfp(StringIO(self._zf.read(filename)))
        if cp.has_option('Library', parameter):
            return cp.get('Library', parameter)
        else:
            return ''

    def _complete(self, result):
        GLib.idle_add(self.emit, 'complete', result, self._size,
                      self._icon_file_name)
