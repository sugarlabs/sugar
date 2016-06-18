# Copyright (C) 2013, Walter Bender - Raul Gutierrez Segales
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


from gi.repository import Gtk

from jarabe.webservice import accountsmanager

from cpsection.webaccount.web_service import WebService

_SERVICE_NAME = 'mock'


class WebService(WebService):

    def __init__(self):
        self._account = accountsmanager.get_account(_SERVICE_NAME)

    def get_icon_name(self):
        return _SERVICE_NAME

    def config_service_cb(self, widget, event, container):
        label = Gtk.Label(_SERVICE_NAME)

        for c in container.get_children():
            container.remove(c)

        container.add(label)
        container.show_all()


def get_service():
    return WebService()
