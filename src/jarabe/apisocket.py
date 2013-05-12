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
import struct
import time

import dbus
from gi.repository import GConf
from gi.repository import GLib
from gwebsockets.server import Server
from gwebsockets.server import Message

from sugar3 import env

from jarabe.model import shell


class StreamMonitor:
    def __init__(self):
        self.on_data = None
        self.on_close = None


class API:
    def __init__(self, client):
        self._client = client

        self._activity = None
        for activity in shell.get_model():
            if activity.get_activity_id() == client.activity_id:
                self._activity = activity


class ActivityAPI(API):
    def get_xo_color(self, request):
        gconf_client = GConf.Client.get_default()
        color_string = gconf_client.get_string('/desktop/sugar/user/color')

        self._client.send_result(request, color_string.split(","))

    def close(self, request):
        self._activity.get_window().close(GLib.get_current_time())

        self._client.send_result(request, None)


class DatastoreAPI(API):
    def __init__(self, client):
        API.__init__(self, client)

        bus = dbus.SessionBus()
        bus_object = bus.get_object("org.laptop.sugar.DataStore",
                                    "/org/laptop/sugar/DataStore")
        self._data_store = dbus.Interface(bus_object,
                                          "org.laptop.sugar.DataStore")

    def _create_file(self):
        activity_root = env.get_profile_path(self._activity.get_type())
        instance_path = os.path.join(activity_root, "instance")

        file_path = os.path.join(instance_path, "%i" % time.time())
        file_object = open(file_path, "w")

        return file_path, file_object

    def load(self, request):
        def reply_handler(file_name):
            file_object = open(file_name)
            info["file_object"] = file_object

            if "requested_size" in info:
                data = file_object.read(info["requested_size"])
                self._client.send_binary(data)

            if "stream_closed" in info:
                complete()

        def error_handler(error):
            self._client.send_error(request, error)

        def on_data(data):
            size = struct.unpack("ii", data)[1]
            if "file_object" in info:
                self._client.send_binary(info["file_object"].read(size))
            else:
                info["requested_size"] = size

        def on_close():
            if "file_object" in info:
                complete()
            else:
                info["stream_closed"] = True

        def complete():
            info["file_object"].close()
            self._client.send_result(request, None)

        info = {}

        uid, stream_id = request["params"]

        self._data_store.get_filename(uid,
                                      reply_handler=reply_handler,
                                      error_handler=error_handler)

        stream_monitor = self._client.stream_monitors[stream_id]
        stream_monitor.on_data = on_data
        stream_monitor.on_close = on_close

    def update(self, request):
        def reply_handler():
            self._client.send_result(request, None)

        def error_handler(error):
            self._client.send_error(request, error)

        def on_data(data):
            file_object.write(data[1:])

        def on_close():
            file_object.close()
            self._data_store.update(uid, metadata, file_path, True,
                                    reply_handler=reply_handler,
                                    error_handler=error_handler)

        uid, metadata, stream_id = request["params"]

        file_path, file_object = self._create_file()

        stream_monitor = self._client.stream_monitors[stream_id]
        stream_monitor.on_data = on_data
        stream_monitor.on_close = on_close

    def create(self, request):
        def reply_handler(object_id):
            self._client.send_result(request, object_id)

        def error_handler(error):
            self._client.send_error(request, error)

        def on_data(data):
           file_object.write(data)

        def on_close():
            file_object.close()
            self._data_store.create(metadata, file_path, True,
                                    reply_handler=reply_handler,
                                    error_handler=error_handler)

        metadata, stream_id = request["params"]

        file_path, file_object = self._create_file()

        stream_monitor = self._client.stream_monitors[stream_id]
        stream_monitor.on_data = on_data
        stream_monitor.on_close = on_close


class APIClient:
    def __init__(self, session):
        self._session = session

        self.activity_id = None
        self.stream_monitors = {}

    def send_result(self, request, result):
        response = {"result": result,
                    "error": None,
                    "id": request["id"]}

        self._session.send_message(json.dumps(response))

    def send_error(self, request, error):
        response = {"result": None,
                    "error": error,
                    "id": request["id"]}

        self._session.send_message(json.dumps(response))

    def send_binary(self, data):
        self._session.send_message(data, binary=True)


class APIServer:
    def __init__(self):
        self._stream_monitors = {}

        self._server = Server()
        self._server.connect("session-started", self._session_started_cb)
        self._port = self._server.start()
        self._key = os.urandom(16).encode("hex")

        self._apis = {}
        self._apis["activity"] = ActivityAPI
        self._apis["datastore"] = DatastoreAPI

    def setup_environment(self):
        os.environ["SUGAR_APISOCKET_PORT"] = str(self._port)
        os.environ["SUGAR_APISOCKET_KEY"] = self._key

    def _open_stream(self, client, request):
        for stream_id in xrange(0, 255):
            if stream_id not in client.stream_monitors:
                client.stream_monitors[stream_id] = StreamMonitor()
                break

        client.send_result(request, stream_id)

    def _close_stream(self, client, request):
        stream_id = request["params"][0]
        stream_monitor = client.stream_monitors[stream_id]
        if stream_monitor.on_close:
            stream_monitor.on_close()

        del client.stream_monitors[stream_id]

        client.send_result(request, None)

    def _session_started_cb(self, server, session):
        session.connect("message-received",
                        self._message_received_cb, APIClient(session))

    def _message_received_cb(self, session, message, client):
        if message.message_type == Message.TYPE_BINARY:
            stream_id = ord(message.data[0])
            stream_monitor = client.stream_monitors[stream_id]
            stream_monitor.on_data(message.data)
            return

        request = json.loads(message.data)

        if request["method"] == "authenticate":
            params = request["params"]
            if self._key == params[1]:
                client.activity_id = params[0]
                return

        activity_id = client.activity_id
        if activity_id is None:
            return

        if request["method"] == "open_stream":
            self._open_stream(client, request)
        elif request["method"] == "close_stream":
            self._close_stream(client, request)
        else:
            api_name, method_name = request["method"].split(".")
            getattr(self._apis[api_name](client), method_name)(request)


def start():
    server = APIServer()
    server.setup_environment()
