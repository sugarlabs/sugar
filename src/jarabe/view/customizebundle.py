# Copyright (C) 2011 Walter Bender
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
import glob
import hashlib

from gi.repository import Gtk

from sugar3 import profile
from sugar3.activity import bundlebuilder
from sugar3.datastore import datastore
from sugar3.env import get_user_activities_path

import logging
_logger = logging.getLogger('CustomizeBundle')


BADGE_SUBPATH = 'emblems/emblem-view-source.svg'
BADGE_TRANSFORM = '  <g transform="matrix(0.45,0,0,0.45,32,32)">\n'
ICON_TRANSFORM = ' <g transform="matrix(1.0,0,0,1.0,0,0)">\n'
XML_HEADER = '<?xml version="1.0" ?> \
<!DOCTYPE svg  PUBLIC "-//W3C//DTD SVG 1.1//EN" \
"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd" [\n\
<!ENTITY stroke_color "#010101">\n\
<!ENTITY fill_color "#FFFFFF">\n]>\n'
SVG_START = '<svg enable-background="new 0 0 55 55" height="55px" \
version="1.1" viewBox="0 0 55 55" width="55px" x="0px" xml:space="preserve" \
xmlns="http://www.w3.org/2000/svg" \
xmlns:xlink="http://www.w3.org/1999/xlink" y="0px">\n'
SVG_END = '</svg>\n'


def generate_unique_id():
    """Generate an id based on the user's nick name and their public key
    (Based on schema used by IRC activity).

    """
    nick = profile.get_nick_name()
    pubkey = profile.get_pubkey()
    m = hashlib.sha1()
    m.update(pubkey)
    hexhash = m.hexdigest()

    nick_letters = "".join([x for x in nick if x.isalpha()])

    if not nick_letters:
        nick_letters = 'XO'

    return nick_letters + '_' + hexhash[:4]


def generate_bundle(nick, new_basename):
    """Generate a new .xo bundle for the activity and copy it into the
    Journal.

    """
    new_activity_name = _customize_activity_info(
        nick, new_basename)

    user_activities_path = get_user_activities_path()
    if os.path.exists(os.path.join(user_activities_path, new_basename,
                                   'dist')):
        for path in glob.glob(os.path.join(user_activities_path, new_basename,
                                           'dist', '*')):
            os.remove(path)

    source_dir = os.path.join(user_activities_path, new_basename)
    config = bundlebuilder.Config(
        source_dir=source_dir,
        dist_dir=os.path.join(source_dir, 'dist'),
        dist_name='%s-1' % (new_activity_name))
    bundlebuilder.cmd_dist_xo(config, None)

    dsobject = datastore.create()
    dsobject.metadata['title'] = '%s-1.xo' % (new_activity_name)
    dsobject.metadata['mime_type'] = 'application/vnd.olpc-sugar'
    dsobject.set_file_path(os.path.join(
        user_activities_path, new_basename, 'dist',
        '%s-1.xo' % (new_activity_name)))
    datastore.write(dsobject)
    dsobject.destroy()


def _customize_activity_info(nick, new_basename):
    """Modify bundle_id in new activity.info file:
    (1) change the bundle_id to bundle_id_[NICKNAME];
    (2) change the activity_icon [NICKNAME]-activity-icon.svg;
    (3) set activity_version to 1;
    (4) modify the activity icon by applying a customize overlay.

    """
    new_activity_name = ''
    user_activities_path = get_user_activities_path()

    info_old = open(os.path.join(user_activities_path, new_basename,
                                 'activity', 'activity.info'), 'r')
    info_new = open(os.path.join(user_activities_path, new_basename,
                                 'activity', 'new_activity.info'), 'w')

    for line in info_old:
        if line.find('=') < 0:
            info_new.write(line)
            continue
        name, value = [token.strip() for token in line.split('=', 1)]
        if name == 'bundle_id':
            new_value = '%s_%s' % (value, nick)
        elif name == 'activity_version':
            new_value = '1'
        elif name == 'icon':
            new_value = value
            icon_name = value
        elif name == 'name':
            new_value = '%s_copy_of_%s' % (nick, value)
            new_activity_name = new_value
        else:
            info_new.write(line)
            continue

        info_new.write('%s = %s\n' % (name, new_value))

    info_old.close()
    info_new.close()

    os.rename(os.path.join(user_activities_path, new_basename,
                           'activity', 'new_activity.info'),
              os.path.join(user_activities_path, new_basename,
                           'activity', 'activity.info'))

    _create_custom_icon(new_basename, icon_name)

    return new_activity_name


def _create_custom_icon(new_basename, icon_name):
    """Modify activity icon by overlaying a badge:
    (1) Extract the payload from the badge icon;
    (2) Add a transform to resize it and position it;
    (3) Insert it into the activity icon.

    """
    user_activities_path = get_user_activities_path()
    badge_path = None
    for path in Gtk.IconTheme.get_default().get_search_path():
        if os.path.exists(os.path.join(path, 'sugar', 'scalable',
                                       BADGE_SUBPATH)):
            badge_path = path
            break

    if badge_path is None:
        _logger.debug('%s not found', BADGE_SUBPATH)
        return

    badge_fd = open(os.path.join(badge_path, 'sugar', 'scalable',
                                 BADGE_SUBPATH), 'r')
    badge_payload = _extract_svg_payload(badge_fd)
    badge_fd.close()

    badge_svg = BADGE_TRANSFORM + badge_payload + '\n</g>'

    icon_path = os.path.join(user_activities_path, new_basename, 'activity',
                             icon_name + '.svg')
    icon_fd = open(icon_path, 'r')
    icon_payload = _extract_svg_payload(icon_fd)
    icon_fd.close()

    icon_svg = ICON_TRANSFORM + icon_payload + '\n</g>'

    tmp_path = os.path.join(user_activities_path, new_basename, 'activity',
                            'tmp.svg')
    tmp_icon_fd = open(tmp_path, 'w')
    tmp_icon_fd.write(XML_HEADER)
    tmp_icon_fd.write(SVG_START)
    tmp_icon_fd.write(icon_svg)
    tmp_icon_fd.write(badge_svg)
    tmp_icon_fd.write(SVG_END)
    tmp_icon_fd.close()

    os.remove(icon_path)
    os.rename(tmp_path, icon_path)


def _extract_svg_payload(fd):
    """Returns everything between <svg ...> and </svg>"""
    payload = ''
    looking_for_start_svg_token = True
    looking_for_close_token = True
    looking_for_end_svg_token = True
    for line in fd:
        if looking_for_start_svg_token:
            if line.find('<svg') < 0:
                continue
            looking_for_start_svg_token = False
            line = line.split('<svg', 1)[1]
        if looking_for_close_token:
            if line.find('>') < 0:
                continue
            looking_for_close_token = False
            line = line.split('>', 1)[1]
        if looking_for_end_svg_token:
            if line.find('</svg>') < 0:
                payload += line
                continue
            payload += line.split('</svg>')[0]
            break
    return payload
