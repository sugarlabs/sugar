# Copyright (C) 2013, Daniel Narvaez
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

import json
import os
import struct
import time

import dbus
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gio
from gwebsockets.server import Server
from gwebsockets.server import Message

from sugar3 import env

from jarabe.model import shell
from jarabe.model import session
from jarabe.journal.objectchooser import ObjectChooser


class StreamMonitor(object):

    def __init__(self):
        self.on_data = None
        self.on_close = None


class API(object):

    def __init__(self, client):
        self._client = client

        self._activity = None
        for activity in shell.get_model():
            if activity.get_activity_id() == client.activity_id:
                self._activity = activity


class ActivityAPI(API):

    def __init__(self, client):
        API.__init__(self, client)
        self._activity.connect('pause', self._pause_cb)
        self._activity.connect('resume', self._resume_cb)
        self._activity.connect('stop', self._stop_cb)

        session.get_session_manager().shutdown_signal.connect(
            self._session_manager_shutdown_cb)

    def get_xo_color(self, request):
        settings = Gio.Settings('org.sugarlabs.user')
        color_string = settings.get_string('color')

        self._client.send_result(request, [color_string.split(",")])

    def close(self, request):
        self._activity.get_window().close(GLib.get_current_time())

        self._client.send_result(request, [])

    def _pause_cb(self, event):
        self._client.send_notification("activity.pause")

    def _resume_cb(self, event):
        self._client.send_notification("activity.resume")

    def _stop_cb(self, event):
        # When the web activity receives this notification, it has
        # time for saving the state and do any cleanup needed.  Then
        # it must call 'window.close' to complete the activity
        # closing.
        self._client.send_notification("activity.stop")
        return True

    def _session_manager_shutdown_cb(self, event):
        self._client.send_notification("activity.stop")

    def show_object_chooser(self, request):
        chooser = ObjectChooser(self._activity)
        chooser.connect('response', self._chooser_response_cb, request)
        chooser.show()

    def _chooser_response_cb(self, chooser, response_id, request):
        if response_id == Gtk.ResponseType.ACCEPT:
            object_id = chooser.get_selected_object_id()
            self._client.send_result(request, [object_id])
        else:
            self._client.send_result(request, [None])

        chooser.destroy()


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

    def get_metadata(self, request):
        def get_properties_reply_handler(properties):
            self._client.send_result(request, [properties])

        def error_handler(error):
            self._client.send_error(request, error)

        self._data_store.get_properties(
            request["params"][0], byte_arrays=True,
            reply_handler=get_properties_reply_handler,
            error_handler=error_handler)

    def set_metadata(self, request):
        def reply_handler():
            self._client.send_result(request, [])

        def error_handler(error):
            self._client.send_error(request, error)

        uid, metadata = request["params"]

        self._data_store.update(uid, metadata, "", True,
                                reply_handler=reply_handler,
                                error_handler=error_handler)

    def load(self, request):
        def get_filename_reply_handler(file_name):
            file_object = open(file_name)
            info["file_object"] = file_object

            if "requested_size" in info:
                send_binary(file_object.read(info["requested_size"]))

            if "stream_closed" in info:
                info["file_object"].close()

        def get_properties_reply_handler(properties):
            self._client.send_result(request, [properties])

        def error_handler(error):
            self._client.send_error(request, error)

        def send_binary(data):
            self._client.send_binary(chr(stream_id) + data)

        def on_data(data):
            size = struct.unpack("ii", data)[1]
            if "file_object" in info:
                send_binary(info["file_object"].read(size))
            else:
                info["requested_size"] = size

        def on_close(close_request):
            if "file_object" in info:
                info["file_object"].close()
            else:
                info["stream_closed"] = True

            self._client.send_result(close_request, [])

        info = {}

        uid, stream_id = request["params"]

        self._data_store.get_filename(
            uid,
            reply_handler=get_filename_reply_handler,
            error_handler=error_handler)

        self._data_store.get_properties(
            uid, byte_arrays=True,
            reply_handler=get_properties_reply_handler,
            error_handler=error_handler)

        stream_monitor = self._client.stream_monitors[stream_id]
        stream_monitor.on_data = on_data
        stream_monitor.on_close = on_close

    def save(self, request):
        def reply_handler():
            self._client.send_result(info["close_request"], [])

        def error_handler(error):
            self._client.send_error(info["close_request"], error)

        def on_data(data):
            file_object.write(data[1:])

        def on_close(close_request):
            file_object.close()

            info["close_request"] = close_request
            self._data_store.update(uid, metadata, file_path, True,
                                    reply_handler=reply_handler,
                                    error_handler=error_handler)

        info = {}

        uid, metadata, stream_id = request["params"]

        file_path, file_object = self._create_file()

        stream_monitor = self._client.stream_monitors[stream_id]
        stream_monitor.on_data = on_data
        stream_monitor.on_close = on_close

        self._client.send_result(request, [])

    def create(self, request):
        def reply_handler(object_id):
            self._client.send_result(request, [object_id])

        def error_handler(error):
            self._client.send_error(request, error)

        self._data_store.create(request["params"][0], "", True,
                                reply_handler=reply_handler,
                                error_handler=error_handler)


class APIClient(object):

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

    def send_notification(self, method, params=None):
        if params is None:
            params = []

        response = {"method": method,
                    "params": params}

        self._session.send_message(json.dumps(response))

    def send_binary(self, data):
        self._session.send_message(data, binary=True)


class APIServer(object):

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

        client.send_result(request, [stream_id])

    def _close_stream(self, client, request):
        stream_id = request["params"][0]
        stream_monitor = client.stream_monitors[stream_id]
        if stream_monitor.on_close:
            stream_monitor.on_close(request)

        del client.stream_monitors[stream_id]

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
