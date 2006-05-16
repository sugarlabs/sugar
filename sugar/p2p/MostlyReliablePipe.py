import socket
import time
import sha
import struct
import StringIO
import binascii

import pygtk
pygtk.require('2.0')
import gtk, gobject


_MTU = 482
_HEADER_LEN = 30
_MAGIC = 0xbaea4304
_TTL = 120 # 2 minutes

class MessageSegment(object):
	# 4: magic (0xbaea4304)
	# 2: segment number
	# 2: total segments
	# 2: data size
	#20: total message sha1
	_HEADER_TEMPLATE = "! IHHH20s"

	def _new_from_parts(self, num, all, data, master_sha):
		if not data:
			raise ValueError("Must have valid data.")
		if num > 65535:
			raise ValueError("Segment number cannot be more than 65535.")
		if num < 1:
			raise ValueError("Segment number must be greater than zero.")
		if all > 65535:
			raise ValueError("Message cannot have more than 65535 segments.")
		if all < 1:
			raise ValueError("Message must have at least one segment.")
		self._stime = time.time()
		self._data = data
		self._data_len = len(data)
		self._master_sha = master_sha
		self._num = num
		self._all = all

		self._header = struct.pack(self._HEADER_TEMPLATE, _MAGIC, self._num,
				self._all, self._data_len, self._master_sha)

	def _new_from_data(self, data):
		if len(data) < _HEADER_LEN + 1:
			raise ValueError("Message is less then minimum required length")
		stream = StringIO.StringIO(data)
		self._stime = None
		(magic, num, all, data_len, master_sha) = struct.unpack(self._HEADER_TEMPLATE,
				stream.read(struct.calcsize(self._HEADER_TEMPLATE)))

		# Format checking
		if magic != _MAGIC:
			raise ValueError("Message does not have the correct magic.")
		if not num:
			raise ValueError("Segment number must be greater than 0.")
		if not all:
			raise ValueError("Message must have at least one segment.")
		if not data_len:
			raise ValueError("Message must have some data.")
		if data_len > _MTU:
			raise ValueError("Data length must not be larger than the MTU (%s)." % _MTU)

		self._num = num
		self._all = all
		self._data_len = data_len
		self._master_sha = master_sha

		# Read data
		self._data = struct.unpack("! %ds" % self._data_len, stream.read(self._data_len))

	def new_from_parts(num, all, data, master_sha):
		segment = MessageSegment()
		segment._new_from_parts(num, all, data, master_sha)
		return segment
	new_from_parts = staticmethod(new_from_parts)

	def new_from_data(data):
		segment = MessageSegment()
		segment._new_from_data(data)
		return segment
	new_from_data = staticmethod(new_from_data)

	def stime(self):
		return self._stime

	def num(self):
		return self._num

	def all(self):
		return self._all

	def data(self):
		return self._data

	def header(self):
		return self._header

	def master_sha(self):
		return self._master_sha

	def segment(self):
		"""Return a correctly formatted message that can be immediately sent."""
		return self._header + self._data

class MostlyReliablePipe(object):
	"""Implement Mostly-Reliable UDP.  We don't actually care about guaranteeing
	delivery or receipt, just a better effort than no effort at all."""

	def __init__(self, local_addr, remote_addr, port, data_cb, user_data=None):
		self._local_addr = local_addr
		self._remote_addr = remote_addr
		self._port = port
		self._data_cb = data_cb
		self._user_data = user_data
		self._started = False
		self._outgoing = []
		self._sent = []
		self._worker = 0

		self._setup_listener()
		self._setup_sender()

	def _setup_sender(self):
		self._send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		# Make the socket multicast-aware, and set TTL.
		self._send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 20) # Change TTL (=20) to suit

	def _setup_listener(self):
		# Listener socket
		self._listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

		# Set some options to make it multicast-friendly
		self._listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self._listen_sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_TTL, 20)
		self._listen_sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_LOOP, 1)

	def start(self):
		# Set some more multicast options
		self._listen_sock.bind((self._local_addr, self._port))  # Bind to all interfaces
		self._listen_sock.settimeout(2)
		intf = socket.gethostbyname(socket.gethostname())
		self._listen_sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF,
				socket.inet_aton(intf) + socket.inet_aton('0.0.0.0'))
		self._listen_sock.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP,
				socket.inet_aton(self._remote_addr) + socket.inet_aton('0.0.0.0'))

		# Watch the listener socket for data
		gobject.io_add_watch(self._listen_sock, gobject.IO_IN, self._handle_incoming_data)
		gobject.timeout_add(120000, self._segment_ttl_worker)

		self._started = True

	def _segment_ttl_worker(self):
		now = time.time()
		for segment in self._sent[:]:
			if segment.stime() < now - _MSG_TTL:
				self._sent.remove(segment)
		return True

	def _handle_incoming_data(self, source, condition):
		if not (condition & gobject.IO_IN):
			return True
		msg = {}
		data, addr = source.recvfrom(_MTU + _HEADER_LEN)
		if self._data_cb:
			self._data_cb(addr, data, self._user_data)
		return True

	def send(self, data):
		if not self._started:
			raise Exception("Can't send anything until started!")

		# Pack the data into network byte order
		template = "! %ds" % len(data)
		data = struct.pack(template, data)
		sha_hash = sha.new()
		sha_hash.update(data)
		master_sha = sha_hash.digest()

		# Split up the data into segments
		left = length = len(data)
		nmessages = length / _MTU
		if length % _MTU > 0:
			nmessages = nmessages + 1
		msg_num = 1
		while left > 0:
			msg = MessageSegment.new_from_parts(msg_num, nmessages, data[:_MTU], master_sha)
			self._outgoing.append(msg)
			msg_num = msg_num + 1
			data = data[_MTU:]
			left = left - _MTU
		if len(self._outgoing) > 0 and self._worker == 0:
			self._worker = gobject.idle_add(self._send_worker)

	def _send_worker(self):
		self._worker = 0
		for segment in self._outgoing:
			data = segment.segment()
			self._send_sock.sendto(data, (self._remote_addr, self._port))
		self._sent = self._outgoing
		self._outgoing = []
		return False


def got_data(addr, data, user_data=None):
	segment = MessageSegment.new_from_data(data)
	print "Segment (%d/%d)" % (segment.num(), segment.all())
	print_sha = ""
	for char in segment.master_sha():
		print_sha = print_sha + binascii.b2a_hex(char)
	print "   Master SHA: %s" % print_sha
	print "   Data: '%s'" % segment.data()
	print ""

def main():
	pipe = MostlyReliablePipe('', '224.0.0.222', 2293, got_data)
	pipe.start()
	pipe.send('The quick brown fox jumps over the lazy dog')
	gtk.main()


if __name__ == "__main__":
	main()

