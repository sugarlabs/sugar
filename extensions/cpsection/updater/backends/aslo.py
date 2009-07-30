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
<RDF:RDF xmlns:RDF="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:em="http://www.mozilla.org/2004/em-rdf#"><RDF:Description about="urn:mozilla:extension:bounce">
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
            <em:updateLink>http://activities.sugarlabs.org/downloads/file/25986/bounce-7.xo</em:updateLink>
            
            <em:updateHash>sha256:816a7c43b4f1ea4769c61c03fea24842ec5fa566b7d41626ffc52ec37b37b6c5</em:updateHash>
        </RDF:Description>
    </em:targetApplication>
</RDF:Description></RDF:RDF>
"""

import urllib2
from urllib2 import HTTPError

import socket

from  xml.etree.ElementTree import ElementTree, XML

from jarabe import config

class ASLOParser():
    """XML parser to pull out data expressed in our aslo format."""
    
    def __init__(self, xml_data):
        self.elem = XML(xml_data)

    def parse(self):
        try:
            self.version = self.elem.find(".//{http://www.mozilla.org/2004/em-rdf#}version").text
            self.link = self.elem.find(".//{http://www.mozilla.org/2004/em-rdf#}updateLink").text
            self.size = self.elem.find(".//{http://www.mozilla.org/2004/em-rdf#}updateSize").text
            self.size = long(self.size) * 1024
        except:
            self.version = 0
            self.link = None
            self.size = 0

def parse_aslo(xml_data):
    """Parse the activity information embedded in the given string
    containing XML data.  Returns a list containing the activity version and url.
    """
    ap = ASLOParser(xml_data)
    ap.parse()
    return ap.version, ap.link, ap.size

def parse_url(url):
    """Parse the activity information at the given URL. Returns the same
    information as `parse_xml` does, and raises the same exceptions.
    The `urlopen_args` can be any keyword arguments accepted by
    `bitfrost.util.urlrange.urlopen`."""

    response = urllib2.urlopen(url)
    return parse_aslo(response.read())

def fetch_update_info(bundle):
    """Return a tuple of new version, url for new version.

    All the information about the new version is `None` if no newer
    update can be found.
    """

    url = 'http://activities.sugarlabs.org/services/update.php?id=' + bundle.get_bundle_id() + '&appVersion=' + config.version

    return parse_url(url)

#########################################################################
# Self-test code.
def _main():
    """Self-test."""
    print parse_url('http://activities.sugarlabs.org/services/update.php?id=bounce')

if __name__ == '__main__': _main ()
