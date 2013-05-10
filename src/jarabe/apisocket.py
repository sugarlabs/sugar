# Copyright (C) 2013 Daniel Narvaez
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import json
import os

from gi.repository import GConf
from gi.repository import GLib
from gwebsockets.server import Server

from jarabe.model import shell


class API:
    def __init__(self, activity_id):
        self._activity_id = activity_id


class ActivityAPI(API):
    def get_xo_color(self):
        client = GConf.Client.get_default()
        color_string = client.get_string('/desktop/sugar/user/color')
        return color_string.split(",")

    def close(self):
        for activity in shell.get_model():
            if activity.get_activity_id() == self._activity_id:
                activity.get_window().close(GLib.get_current_time())


class APIClient:
    def __init__(self):
        self.activity_id = None


class APIServer:
    def __init__(self):
        self._server = Server()
        self._server.connect("session-started", self._session_started_cb)
        self._port = self._server.start()
        self._key = os.urandom(16).encode("hex")

        self._apis = {}
        self._apis["activity"] = ActivityAPI

    def setup_environment(self):
        os.environ["SUGAR_APISOCKET_PORT"] = str(self._port)
        os.environ["SUGAR_APISOCKET_KEY"] = self._key

    def _session_started_cb(self, server, session):
        session.connect("message-received",
                        self._message_received_cb, APIClient())

    def _message_received_cb(self, session, message, api_client):
        request = json.loads(message.data)

        if request["method"] == "authenticate":
            params = request["params"]
            if self._key == params[1]:
                api_client.activity_id = params[0]
                return

        activity_id = api_client.activity_id
        if activity_id is None:
            return

        api_name, method_name = request["method"].split(".")
        method = getattr(self._apis[api_name](activity_id), method_name)

        result = method(*request["params"])

        response = {"result": result,
                    "error": None,
                    "id": request["id"]}

        session.send_message(json.dumps(response))


def start():
    server = APIServer()
    server.setup_environment()
