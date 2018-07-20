# Copyright 2013 Daniel Narvaez
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from StringIO import StringIO
from collections import deque

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject

from jarabe.gwebsockets import protocol

logger = logging.getLogger("gwebsockets")


class MessageBuffer():
    def __init__(self):
        self._data = b""
        self.available = 0

    def append(self, data):
        self._data = self._data + data
        self.available = len(self._data)

    def read(self, size):
        result = self._data[:size]
        self._data = self._data[size:]
        self.available = len(self._data)
        return result


class Message():
    TYPE_TEXT = 0
    TYPE_BINARY = 1

    def __init__(self, message_type, data):
        self.message_type = message_type
        self.data = data


class Session(GObject.GObject):
    message_received = GObject.Signal("message-received", arg_types=(object,))

    def __init__(self, connection):
        GObject.GObject.__init__(self)

        self._connection = connection
        self._request = StringIO()
        self._message = MessageBuffer()
        self._parse_g = None
        self._ready = False
        self._send_queue = deque()
        self._sending = False

    def _response_write_cb(self, stream, result, user_data):
        stream.write_bytes_finish(result)
        self._ready = True

    def _do_handshake(self):
        self._request.seek(0)
        response = protocol.make_handshake(self._request)

        stream = self._connection.get_output_stream()
        stream.write_bytes_async(GLib.Bytes.new(response.encode("utf-8")),
                                 GLib.PRIORITY_DEFAULT,
                                 None, self._response_write_cb, None)

    def read_data(self):
        stream = self._connection.get_input_stream()
        stream.read_bytes_async(8192, GLib.PRIORITY_DEFAULT, None,
                                self._read_data_cb, None)

    def _read_data_cb(self, stream, result, user_data):
        data = stream.read_bytes_finish(result).get_data()
        logger.debug("Got data, length %d" % len(data))

        if not data:
            return

        if self._ready:
            self._message.append(data)

            while self._message.available > 0:
                if self._parse_g is None:
                    self._parse_g = protocol.parse_message(self._message)

                parsed_message = self._parse_g.next()
                if parsed_message:
                    self._parse_g = None

                    received = None
                    if parsed_message.tp == protocol.OPCODE_TEXT:
                        received = Message(Message.TYPE_TEXT,
                                           parsed_message.data)
                        logger.debug("Received text message %s" %
                                     received.data)
                    elif parsed_message.tp == protocol.OPCODE_BINARY:
                        received = Message(Message.TYPE_BINARY,
                                           parsed_message.data)
                        logger.debug("Received binary message, length %s" %
                                     len(received.data))
                    if received:
                        self.message_received.emit(received)
                else:
                    break
        else:
            self._request.write(data)
            if data.endswith("\r\n\r\n"):
                self._do_handshake()

        self.read_data()

    def _message_write_cb(self, stream, result, callback):
        written = stream.write_bytes_finish(result)
        if callback:
            callback(written)

        self._sending = False

        self._send_from_queue()

    def send_message(self, message, callback=None, binary=False):
        if binary:
            logger.debug("Sending binary message, length %s" % len(message))
        else:
            logger.debug("Sending text message %s" % message)

        protocol_message = protocol.make_message(message, binary)
        self._send_queue.append((protocol_message, callback))
        self._send_from_queue()

    def _send_from_queue(self):
        if self._sending:
            return

        if not self._send_queue:
            return

        stream = self._connection.get_output_stream()
        message, callback = self._send_queue.popleft()
        stream.write_bytes_async(GLib.Bytes.new(message),
                                 GLib.PRIORITY_DEFAULT,
                                 None, self._message_write_cb, callback)

        self._sending = True


class Server(GObject.GObject):
    session_started = GObject.Signal("session-started", arg_types=(object,))

    def _incoming_connection_cb(self, service, connection, user_data):
        session = Session(connection)
        self.session_started.emit(session)
        session.read_data()

    def start(self):
        service = Gio.SocketService()
        service.connect("incoming", self._incoming_connection_cb)
        return service.add_any_inet_port(None)


if __name__ == "__main__":
    def message_received_cb(session, message):
        session.send_message(message.data)

    def session_started_cb(server, session):
        session.connect("message-received", message_received_cb)

    server = Server()
    server.connect("session-started", session_started_cb)
    port = server.start()

    print "Listening on port %d" % port

    main_loop = GLib.MainLoop()
    main_loop.run()
