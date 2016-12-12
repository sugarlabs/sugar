# Copyright (C) 2009-2013, Sugar Labs
# Copyright (C) 2009, Tomeu Vizoso
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


class BundleUpdate(object):
    def __init__(self, bundle_id, name, version, link, size,
                 icon_file_name=None, optional=False):
        self.bundle_id = bundle_id
        self.name = name
        self.version = version
        self.link = link
        self.size = size
        self.icon_file_name = icon_file_name
        self.optional = optional
