# Copyright (C) 2012 Agustin Zubiaga <aguz@sugarlabs.org>
# Copyright (C) 2013 Sugar Labs
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
#

from gi.repository import Gio

from jarabe.journal.model import get_documents_path
from jarabe.desktop.homebackgroundbox import BACKGROUND_DIR
from jarabe.desktop.homebackgroundbox import BACKGROUND_IMAGE_PATH_KEY
from jarabe.desktop.homebackgroundbox import BACKGROUND_ALPHA_LEVEL_KEY
from jarabe.desktop.homebackgroundbox import DEFAULT_BACKGROUND_ALPHA_LEVEL

import os

BACKGROUNDS_DIRS = (os.path.join('/usr', 'share', 'backgrounds'),
                    get_documents_path())


def set_background_image_path(file_path):
    settings = Gio.Settings(BACKGROUND_DIR)
    if file_path is None:
        settings.set_string(BACKGROUND_IMAGE_PATH_KEY, '')
    else:
        settings.set_string(BACKGROUND_IMAGE_PATH_KEY, str(file_path))
    return 1


def get_background_image_path():
    settings = Gio.Settings(BACKGROUND_DIR)
    return settings.get_string(BACKGROUND_IMAGE_PATH_KEY)

PREVIOUS_BACKGROUND_IMAGE_PATH = get_background_image_path()


def set_background_alpha_level(alpha_level):
    settings = Gio.Settings(BACKGROUND_DIR)
    settings.set_string(BACKGROUND_ALPHA_LEVEL_KEY, str(alpha_level))


def get_background_alpha_level():
    settings = Gio.Settings(BACKGROUND_DIR)
    alpha = settings.get_string(BACKGROUND_ALPHA_LEVEL_KEY)
    if alpha is None:
        alpha = DEFAULT_BACKGROUND_ALPHA_LEVEL
    else:
        try:
            alpha = float(alpha)
        except ValueError:
            alpha = DEFAULT_BACKGROUND_ALPHA_LEVEL
        if alpha < 0:
            alpha = 0
        elif alpha > 1.0:
            alpha = 1.0
    return alpha

PREVIOUS_BACKGROUND_ALPHA_LEVEL = get_background_alpha_level()


def undo(store):
    set_background_image_path(PREVIOUS_BACKGROUND_IMAGE_PATH)
    set_background_alpha_level(PREVIOUS_BACKGROUND_ALPHA_LEVEL)
