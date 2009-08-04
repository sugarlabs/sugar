#!/usr/bin/python
# Copyright (C) 2009, Sugar Labs
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
import urllib2
from xml.etree.ElementTree import XML
import traceback

from jarabe import config

_FIND_DESCRIPTION = \
        './/{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description'
_FIND_VERSION = './/{http://www.mozilla.org/2004/em-rdf#}version'
_FIND_LINK = './/{http://www.mozilla.org/2004/em-rdf#}updateLink'
_FIND_SIZE = './/{http://www.mozilla.org/2004/em-rdf#}updateSize'

_UPDATE_PATH = 'http://activities.sugarlabs.org/services/update.php'

def _parse_url(url, bundle_id):
    response = urllib2.urlopen(url)
    document = XML(response.read())

    if document.find(_FIND_DESCRIPTION) is None:
        logging.debug('Bundle %s not available in the server for the version'
                      ' %s' % (bundle_id, config.version))
        return '0', None, 0

    version = document.find(_FIND_VERSION).text
    link = document.find(_FIND_LINK).text
    size = long(document.find(_FIND_SIZE).text) * 1024

    return version, link, size

def fetch_update_info(bundle):
    """Return a tuple of (version, link, size_in_bytes) for new version.

    Returns ('0', None, 0) if no update is found for the platform version.
    """

    url = '%s?id=%s&appVersion=%s' % \
            (_UPDATE_PATH, bundle.get_bundle_id(), '0.84.1') #config.version)

    return _parse_url(url, bundle.get_bundle_id())

#########################################################################
# Self-test code.
def _main():
    """Self-test."""
    print _parse_url('%s?id=bounce' % _UPDATE_PATH, 'bounce')

if __name__ == '__main__':
    _main()

