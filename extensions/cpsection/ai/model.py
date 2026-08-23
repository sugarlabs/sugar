# Copyright (C) 2026, Sugar Labs (Shubham Sharma)
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

import configparser
import logging
import os
import tempfile

from jarabe.journal import reflection

_SECTION = 'reflection'


def _read_parser():
    # interpolation=None keeps '%' in urls and keys literal.
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read(reflection.DEFAULT_CONFIG_PATH)
    except (configparser.Error, OSError, ValueError):
        # A file we cannot parse holds nothing we could edit, and a
        # half-read parser is worse than an empty one: start over, so
        # the panel opens and the next write lays down a sound file.
        logging.exception('ai: error reading %r',
                          reflection.DEFAULT_CONFIG_PATH)
        parser = configparser.ConfigParser(interpolation=None)
    if not parser.has_section(_SECTION):
        parser.add_section(_SECTION)
    return parser


# The getters read the file itself, not reflection.read_config():
# that merged view includes environment overrides, and an editor
# that round-trips them through undo would bake them into the file.

def get_enabled():
    try:
        return _read_parser().getboolean(
            _SECTION, 'enabled', fallback=reflection.DEFAULT_ENABLED)
    except ValueError:
        return reflection.DEFAULT_ENABLED


def get_url():
    return _read_parser().get(_SECTION, 'url', fallback='')


def get_api_key():
    return _read_parser().get(_SECTION, 'api_key', fallback='')


def set_enabled(enabled):
    _write_option('enabled', 'true' if enabled else 'false')


def set_url(url):
    _write_option('url', url.strip())


def set_api_key(api_key):
    _write_option('api_key', api_key.strip())


def _write_option(option, value):
    path = reflection.DEFAULT_CONFIG_PATH
    parser = _read_parser()
    parser.set(_SECTION, option, value)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        _write_parser(parser, path)
    except OSError:
        # A read-only home must not trap the child in the panel:
        # Cancel walks the same setters back.
        logging.exception('ai: error writing %r', path)


def _write_parser(parser, path):
    # The file may hold a server key; never leave it readable to
    # others, not even between creation and a later chmod. The rename
    # lands whole, so a failed write cannot leave a truncated key for
    # the journal to read.
    fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(path),
                                     prefix='reflection.conf.')
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w') as config_file:
            parser.write(config_file)
        os.replace(temp_path, path)
    except OSError:
        os.unlink(temp_path)
        raise
