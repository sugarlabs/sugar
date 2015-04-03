#!/usr/bin/python
# Copyright (C) 2009-2013 Sugar Labs
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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

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
import traceback

from gi.repository import Gio
from gi.repository import GLib

from sugar3.bundle.bundleversion import NormalizedVersion
from sugar3.bundle.bundleversion import InvalidVersionError

from jarabe import config

_FIND_DESCRIPTION = \
        './/{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description'
_FIND_VERSION = './/{http://www.mozilla.org/2004/em-rdf#}version'
_FIND_LINK = './/{http://www.mozilla.org/2004/em-rdf#}updateLink'
_FIND_SIZE = './/{http://www.mozilla.org/2004/em-rdf#}updateSize'

_UPDATE_PATH = 'http://activities.sugarlabs.org/services/update-aslo.php'

_fetcher = None


class _UpdateFetcher(object):

    _CHUNK_SIZE = 10240

    def __init__(self, bundle, completion_cb):
        # ASLO knows only about stable SP releases
        major, minor = config.version.split('.')[0:2]
        sp_version = '%s.%s' % (major, int(minor) + int(minor) % 2)

        url = '%s?id=%s&appVersion=%s' % \
                (_UPDATE_PATH, bundle.get_bundle_id(), sp_version)

        logging.debug('Fetch %s', url)

        self._completion_cb = completion_cb
        self._file = Gio.File.new_for_uri(url)
        self._stream = None
        self._xml_data = ''
        self._bundle = bundle

        self._file.read_async(GLib.PRIORITY_DEFAULT, None,
                              self.__file_read_async_cb, None)

    def __file_read_async_cb(self, gfile, result, user_data):
        try:
            self._stream = self._file.read_finish(result)
        except:
            global _fetcher
            _fetcher = None
            self._completion_cb(None, None, None, None, traceback.format_exc())
            return

        self._stream.read_bytes_async(self._CHUNK_SIZE, GLib.PRIORITY_DEFAULT,
                                      None, self.__stream_read_async_cb, None)

    def __stream_read_async_cb(self, stream, result, user_data):
        data = stream.read_bytes_finish(result)
        if data is None:
            global _fetcher
            _fetcher = None
            self._completion_cb(self._bundle, None, None, None,
                    'Error reading update information for %s from '
                    'server.' % self._bundle.get_bundle_id())
            return
        elif data.get_size() == 0:
            stream.close(None)
            self._process_result()
            return
        else:
            xml_data = data.get_data()
            self._xml_data += str(xml_data)

        stream.read_bytes_async(self._CHUNK_SIZE, GLib.PRIORITY_DEFAULT, None,
                                self.__stream_read_async_cb, None)

    def _process_result(self):
        if self._xml_data is None:
            logging.error('No XML update data returned from ASLO')
            return

        document = XML(self._xml_data)

        if document.find(_FIND_DESCRIPTION) is None:
            logging.debug('Bundle %s not available in the server for the '
                'version %s', self._bundle.get_bundle_id(), config.version)
            version = None
            link = None
            size = None
        else:
            try:
                version = NormalizedVersion(document.find(_FIND_VERSION).text)
            except InvalidVersionError:
                logging.exception('Exception occured while parsing version')
                version = '0'

            link = document.find(_FIND_LINK).text

            try:
                size = long(document.find(_FIND_SIZE).text) * 1024
            except ValueError:
                logging.exception('Exception occured while parsing size')
                size = 0

        global _fetcher
        _fetcher = None
        self._completion_cb(self._bundle, version, link, size, None)


def fetch_update_info(bundle, completion_cb):
    """Queries the server for a newer version of the ActivityBundle.

       completion_cb receives bundle, version, link, size and possibly
       an error message:

       def completion_cb(bundle, version, link, size, error_message):
    """
    global _fetcher

    if _fetcher is not None:
        raise RuntimeError('Multiple simultaneous requests are not supported')

    _fetcher = _UpdateFetcher(bundle, completion_cb)
