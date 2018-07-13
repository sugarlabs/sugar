# Copyright 2013 Open Source, Daniel Narvaez
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

# Based on
# https://code.google.com/p/tulip/source/browse/tulip/http/websocket.py

import base64
import binascii
import collections
import hashlib
import httplib
import struct

OPCODE_CONTINUATION = 0x0
MSG_TEXT = OPCODE_TEXT = 0x1
MSG_BINARY = OPCODE_BINARY = 0x2
MSG_CLOSE = OPCODE_CLOSE = 0x8
MSG_PING = OPCODE_PING = 0x9
MSG_PONG = OPCODE_PONG = 0xa

WS_KEY = b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
WS_HDRS = ('UPGRADE', 'CONNECTION',
           'SEC-WEBSOCKET-VERSION', 'SEC-WEBSOCKET-KEY')

Message = collections.namedtuple('Message', ['tp', 'data', 'extra'])


class BadRequestException(httplib.HTTPException):
    code = 400


class WebSocketError(Exception):
    """WebSocket protocol parser error."""


def parse_frame(buf):
    """Return the next frame from the socket."""
    # read header
    while buf.available < 2:
        yield

    data = buf.read(2)
    first_byte, second_byte = struct.unpack('!BB', data)

    fin = (first_byte >> 7) & 1
    rsv1 = (first_byte >> 6) & 1
    rsv2 = (first_byte >> 5) & 1
    rsv3 = (first_byte >> 4) & 1
    opcode = first_byte & 0xf

    # frame-fin = %x0 ; more frames of this message follow
    #           / %x1 ; final frame of this message
    # frame-rsv1 = %x0 ; 1 bit, MUST be 0 unless negotiated otherwise
    # frame-rsv2 = %x0 ; 1 bit, MUST be 0 unless negotiated otherwise
    # frame-rsv3 = %x0 ; 1 bit, MUST be 0 unless negotiated otherwise
    if rsv1 or rsv2 or rsv3:
        raise WebSocketError('Received frame with non-zero reserved bits')

    if opcode > 0x7 and fin == 0:
        raise WebSocketError('Received fragmented control frame')

    if fin == 0 and opcode == OPCODE_CONTINUATION:
        raise WebSocketError(
            'Received new fragment frame with non-zero opcode')

    has_mask = (second_byte >> 7) & 1
    length = (second_byte) & 0x7f

    # Control frames MUST have a payload length of 125 bytes or less
    if opcode > 0x7 and length > 125:
        raise WebSocketError(
            "Control frame payload cannot be larger than 125 bytes")

    # read payload
    if length == 126:
        while buf.available < 2:
            yield

        length = struct.unpack_from('!H', buf.read(2))[0]
    elif length > 126:
        while buf.available < 4:
            yield

        length = struct.unpack_from('!Q', buf.read(4))[0]

    if has_mask:
        while buf.available < 4:
            yield

        mask = buf.read(4)

    if length:
        while buf.available < length:
            yield

        payload = buf.read(length)
    else:
        payload = b''

    if has_mask:
        mask = [ord(i) for i in mask]
        payload = [chr(ord(b) ^ mask[i % 4]) for i, b in enumerate(payload)]

    yield fin, opcode, payload


def parse_message(buf):
    g = parse_frame(buf)

    while True:
        result = g.next()
        if result:
            break
        else:
            yield

    fin, opcode, payload = result

    if opcode == OPCODE_CLOSE:
        if len(payload) >= 2:
            close_message = "".join(payload[:2])
            close_code = struct.unpack('!H', close_message)[0]
            yield Message(OPCODE_CLOSE, close_code, close_message)
        elif payload:
            raise WebSocketError(
                'Invalid close frame: {} {} {!r}'.format(fin, opcode, payload))

        yield Message(OPCODE_CLOSE, '', '')

    elif opcode == OPCODE_PING:
        yield Message(OPCODE_PING, '', '')

    elif opcode == OPCODE_PONG:
        yield Message(OPCODE_PONG, '', '')

    elif opcode not in (OPCODE_TEXT, OPCODE_BINARY):
        raise WebSocketError("Unexpected opcode={!r}".format(opcode))

    # load text/binary
    data = payload

    g = parse_frame(buf)
    while not fin:
        result = g.next()
        while result is None:
            result = g.next()
            yield

        fin, opcode, payload = result

        if opcode != OPCODE_CONTINUATION:
            raise WebSocketError(
                'The opcode in non-fin frame is expected '
                'to be zero, got {!r}'.format(opcode))
        else:
            data.append(payload)

    if opcode == OPCODE_TEXT:
        yield Message(OPCODE_TEXT, "".join(data), '')
    else:
        yield Message(OPCODE_BINARY, b''.join(data), '')


def _make_frame(message, opcode):
    header = chr(0x80 | opcode)
    msg_length = len(message)

    if msg_length < 126:
        header += chr(msg_length)
    elif msg_length < (1 << 16):
        header += chr(126) + struct.pack('!H', msg_length)
    else:
        header += chr(127) + struct.pack('!Q', msg_length)

    return header + message


def make_pong_message():
    """Make pong message."""
    return _make_frame(b'', OPCODE_PONG)


def make_ping_message():
    """Make ping message."""
    return _make_frame(b'', OPCODE_PING)


def make_close_message(code=1000, message=b''):
    """Close the websocket, sending the specified code and message."""
    return _make_frame(struct.pack('!H%ds' % len(message), code, message),
                       opcode=OPCODE_CLOSE)


def make_message(message, binary=False):
    """Make text message."""
    if isinstance(message, str):
        message = message.encode('utf-8')

    if binary:
        return _make_frame(message, OPCODE_BINARY)
    else:
        return _make_frame(message, OPCODE_TEXT)


def make_handshake(request):
    request_line = request.readline()
    if not request_line.startswith("GET"):
        raise BadRequestException("The method should be GET")

    message = httplib.HTTPMessage(request)
    headers = dict(message)

    if 'websocket' != headers.get('upgrade', '').lower().strip():
        raise BadRequestException('No WebSocket UPGRADE hdr: {}'.format(
            headers.get('upgrade')))

    if 'upgrade' not in headers.get('connection', '').lower():
        raise BadRequestException(
            'No CONNECTION upgrade hdr: {}'.format(
                headers.get('CONNECTION')))

    # check supported version
    version = headers.get('sec-websocket-version')
    if version not in ('13', '8'):
        raise BadRequestException(
            'Unsupported version: {}'.format(version))

    # check client handshake for validity
    key = headers.get('sec-websocket-key')
    try:
        if not key or len(base64.b64decode(key)) != 16:
            raise BadRequestException(
                'Handshake error: {!r}'.format(key))
    except binascii.Error:
        raise BadRequestException(
            'Handshake error: {!r}'.format(key))

    accept_key = hashlib.sha1(key.encode() + WS_KEY).digest()

    return "HTTP/1.1 101 Switching Protocols\r\n" \
           "UPGRADE: websocket\r\n" \
           "CONNECTION: upgrade\r\n" \
           "TRANSFER-ENCODING: chunked\r\n" \
           "SEC-WEBSOCKET-ACCEPT: %s\r\n\r\n" % \
           base64.b64encode(accept_key).decode()
