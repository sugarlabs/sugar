#!/usr/bin/python
# Copyright (C) 2009-2013 Sugar Labs
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


"""Activity information microformat parser.

Activity information is embedded in HTML/XHTML/XML pages using a
Resource Description Framework (RDF) http://www.w3.org/RDF/ .

An example::

<?xml version="1.0" encoding="UTF-8"?>
<RDF:RDF xmlns:RDF="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        xmlns:em="http://www.mozilla.org/2004/em-rdf#">
<RDF:Description about="urn:mozilla:extension:bounce">
    <em:updates>
        <RDF:Seq>
            <RDF:li resource="urn:mozilla:extension:bounce:7"/>
        </RDF:Seq>
    </em:updates>
</RDF:Description>

<RDF:Description about="urn:mozilla:extension:bounce:7">
    <em:version>7</em:version>
    <em:targetApplication>
        <RDF:Description>
            <em:id>{3ca105e0-2280-4897-99a0-c277d1b733d2}</em:id>
            <em:minVersion>0.82</em:minVersion>
            <em:maxVersion>0.84</em:maxVersion>
            <em:updateLink>http://foo.xo</em:updateLink>
            <em:updateSize>7</em:updateSize>
            <em:updateHash>sha256:816a7c43b4f1ea4769c61c03ea4..</em:updateHash>
        </RDF:Description>
    </em:targetApplication>
</RDF:Description></RDF:RDF>
"""

import logging
from xml.etree.ElementTree import XML

from gi.repository import GLib
from gi.repository import GObject

from sugar3.bundle.bundleversion import NormalizedVersion
from sugar3.bundle.bundleversion import InvalidVersionError

from jarabe import config
from jarabe.model.update import BundleUpdate
from jarabe.util.downloader import Downloader

_FIND_DESCRIPTION = \
    './/{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description'
_FIND_VERSION = './/{http://www.mozilla.org/2004/em-rdf#}version'
_FIND_LINK = './/{http://www.mozilla.org/2004/em-rdf#}updateLink'
_FIND_SIZE = './/{http://www.mozilla.org/2004/em-rdf#}updateSize'

_UPDATE_PATH = 'http://activities.sugarlabs.org/services/update-aslo.php'

_logger = logging.getLogger('ASLO')


class _UpdateChecker(GObject.GObject):
    __gsignals__ = {
        'check-complete': (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }
    _CHUNK_SIZE = 10240

    def __init__(self):
        GObject.GObject.__init__(self)
        self._bundle = None

    def check(self, bundle):
        # ASLO knows only about stable SP releases
        major, minor = config.version.split('.')[0:2]
        sp_version = '%s.%s' % (major, int(minor) + int(minor) % 2)

        url = '%s?id=%s&appVersion=%s' % \
            (_UPDATE_PATH, bundle.get_bundle_id(), sp_version)

        self._bundle = bundle

        _logger.debug('Fetch %s', url)
        self._downloader = Downloader(url)
        self._downloader.connect('complete', self.__downloader_complete_cb)
        self._downloader.download()

    def __downloader_complete_cb(self, downloader, result):
        if isinstance(result, Exception):
            self.emit('check-complete', result)
            return

        if result is None:
            _logger.error('No XML update data returned from ASLO')
            return

        document = XML(result.get_data())

        if document.find(_FIND_DESCRIPTION) is None:
            _logger.debug('Bundle %s not available in the server for the '
                          'version %s',
                          self._bundle.get_bundle_id(),
                          config.version)
            version = None
            link = None
            size = None
            self.emit('check-complete', None)
            return

        try:
            version = NormalizedVersion(document.find(_FIND_VERSION).text)
        except InvalidVersionError:
            _logger.exception('Exception occured while parsing version')
            self.emit('check-complete', None)
            return

        link = document.find(_FIND_LINK).text

        try:
            size = long(document.find(_FIND_SIZE).text) * 1024
        except ValueError:
            _logger.exception('Exception occured while parsing size')
            size = 0

        if version > NormalizedVersion(self._bundle.get_activity_version()):
            result = BundleUpdate(self._bundle.get_bundle_id(),
                                  self._bundle.get_name(), version, link, size)
        else:
            result = None

        self.emit('check-complete', result)


class AsloUpdater(object):
    """
    Track state while querying Activites.SugarLabs.Org for activity updates.
    """

    def __init__(self):
        self._completion_cb = None
        self._progress_cb = None
        self._cancelling = False
        self._updates = []
        self._checker = _UpdateChecker()
        self._checker.connect('check-complete', self._check_complete_cb)

    def _check_complete_cb(self, checker, result):
        if isinstance(result, Exception):
            logging.warning("Failed to check bundle: %r", result)
        elif isinstance(result, BundleUpdate):
            self._updates.append(result)

        if self._cancelling:
            self._completion_cb(None)
        else:
            GLib.idle_add(self._check_next_update)

    def _check_next_update(self):
        total = self._total_bundles_to_check
        current = total - len(self._bundles_to_check)
        progress = current / float(total)

        if not self._bundles_to_check:
            self._completion_cb(self._updates)
            return

        bundle = self._bundles_to_check.pop()
        _logger.debug("Checking %s", bundle.get_bundle_id())
        self._progress_cb(bundle.get_name(), progress)
        self._checker.check(bundle)

    def fetch_update_info(self, installed_bundles, auto, progress_cb,
                          completion_cb, error_cb):
        self._completion_cb = completion_cb
        self._progress_cb = progress_cb
        self._error_cb = error_cb
        self._cancelling = False
        self._updates = []
        self._bundles_to_check = installed_bundles
        self._total_bundles_to_check = len(self._bundles_to_check)
        self._check_next_update()

    def cancel(self):
        self._cancelling = True

    def clean(self):
        pass
