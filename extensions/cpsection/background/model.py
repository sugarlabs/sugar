# Copyright (C) 2012 Agustin Zubiaga <aguz@sugarlabs.org>
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
#

import os
import logging

from gi.repository import GConf
from gi.repository import GdkPixbuf

from sugar3.graphics import style
from jarabe.journal.model import get_documents_path

BACKGROUNDS_DIRS = (os.path.join('/usr', 'share', 'backgrounds'),
                    get_documents_path())


def set_background(file_path):
    client = GConf.Client.get_default()
    if file_path is None:
        client.set_string('/desktop/sugar/user/background', '')
    else:
        client.set_string('/desktop/sugar/user/background', str(file_path))
    return 1


def get_background():
    client = GConf.Client.get_default()
    return client.get_string('/desktop/sugar/user/background')


def fill_background_list(store):
    paths_list = []

    for _dir in BACKGROUNDS_DIRS:
        if os.path.exists(_dir) and _dir:
            for bg in os.listdir(_dir):
                path = os.path.join(_dir, bg)
                if os.path.isfile(path):
                    try:
                        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
                            path,
                            style.XLARGE_ICON_SIZE,
                            style.XLARGE_ICON_SIZE)
                        store.append([pixbuf, path])
                        paths_list.append(path)
                    except Exception as e:
                        logging.debug(
                            'Unable to create pixbuf from file %s: %s' % \
                            (path, str(e)))
    return paths_list

BACKGROUND_CHOOSED = get_background()


def undo(store):
    set_background(BACKGROUND_CHOOSED)
