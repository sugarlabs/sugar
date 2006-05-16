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

def _stringify_sha(sha):
	print_sha = ""
	for char in sha:
		print_sha = print_sha + binascii.b2a_hex(char)
	return print_sha

def _sha_data(data):
	sha_hash = sha.new()
	sha_hash.update(data)
	return sha_hash.digest()

class MessageSegment(object):
	# 4: magic (0xbaea4304)
	# 2: segment number
	# 2: total segments
	# 2: message sequence number
	#20: total data sha1
	_HEADER_TEMPLATE = "! IHHH20s"

	def _new_from_parts(self, msg_seq_num, segno, total_segs, data, master_sha):
		"""Construct a new message segment from individual attributes."""
		if not data:
			raise ValueError("Must have valid data.")
		if segno > 65535:
			raise ValueError("Segment number cannot be more than 65535.")
		if segno < 1:
			raise ValueError("Segment number must be greater than zero.")
		if total_segs > 65535:
			raise ValueError("Message cannot have more than 65535 segments.")
		if total_segs < 1:
			raise ValueError("Message must have at least one segment.")
		if msg_seq_num < 1:
			raise ValueError("Message sequence number must be greater than 0.")
		self._stime = time.time()
		self._data = data
		self._data_len = len(data)
		self._master_sha = master_sha
		self._segno = segno
		self._total_segs = total_segs
		self._msg_seq_num = msg_seq_num
		self._addr = None

		# Make the header
		self._header = struct.pack(self._HEADER_TEMPLATE, _MAGIC, self._segno,
				self._total_segs, self._msg_seq_num, self._master_sha)

	def _new_from_data(self, addr, data):
		"""Verify and construct a new message segment from network data."""
		if len(data) < _HEADER_LEN + 1:
			raise ValueError("Message is less then minimum required length")
		stream = StringIO.StringIO(data)
		self._stime = None
		self._addr = addr

		# Determine and verify the length of included data
		stream.seek(0, 2)
		header_size = struct.calcsize(self._HEADER_TEMPLATE)
		self._data_len = stream.tell() - header_size
		if self._data_len < 1:
			raise ValueError("Message must have some data.")
		if self._data_len > _MTU:
			raise ValueError("Data length must not be larger than the MTU (%s)." % _MTU)
		stream.seek(0)

		# Read the header attributes
		(magic, segno, total_segs, msg_seq_num, master_sha) = struct.unpack(self._HEADER_TEMPLATE,
				stream.read(header_size))

		# Sanity checks on the message attributes
		if magic != _MAGIC:
			raise ValueError("Message does not have the correct magic.")
		if segno < 1:
			raise ValueError("Segment number must be greater than 0.")
		if segno > total_segs:
			raise ValueError("Segment number cannot be larger than message segment total.")
		if total_segs < 1:
			raise ValueError("Message must have at least one segment.")
		if msg_seq_num < 1:
			raise ValueError("Message sequence number must be greater than 0.")

		self._segno = segno
		self._total_segs = total_segs
		self._msg_seq_num = msg_seq_num
		self._master_sha = master_sha

		# Reconstruct the data
		self._data = struct.unpack("! %ds" % self._data_len, stream.read(self._data_len))[0]

	def new_from_parts(msg_seq_num, segno, total_segs, data, master_sha):
		"""Static constructor for creation from individual attributes."""
		segment = MessageSegment()
		segment._new_from_parts(msg_seq_num, segno, total_segs, data, master_sha)
		return segment
	new_from_parts = staticmethod(new_from_parts)

	def new_from_data(addr, data):
		"""Static constructor for creation from a packed data stream."""
		segment = MessageSegment()
		segment._new_from_data(addr, data)
		return segment
	new_from_data = staticmethod(new_from_data)

	def stime(self):
		return self._stime

	def addr(self):
		return self._addr

	def segment_number(self):
		return self._segno

	def total_segments(self):
		return self._total_segs

	def message_sequence_number(self):
		return self._msg_seq_num

	def data(self):
		return self._data

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
		self._worker = 0
		self._seq_counter = 0

		self._outgoing = []
		self._sent = []

		self._incoming = {}  # (message sha, # of segments) -> [segment1, segment2, ...]

		self._setup_listener()
		self._setup_sender()

	def _setup_sender(self):
		"""Setup the send socket for multicast."""
		self._send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		# Make the socket multicast-aware, and set TTL.
		self._send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 20) # Change TTL (=20) to suit

	def _setup_listener(self):
		"""Set up the listener socket for multicast traffic."""
		# Listener socket
		self._listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

		# Set some options to make it multicast-friendly
		self._listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self._listen_sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_TTL, 20)
		self._listen_sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_LOOP, 1)

	def start(self):
		"""Let the listener socket start listening for network data."""
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
		"""Cull already-sent message segments that are past their TTL."""
		now = time.time()
		for segment in self._sent[:]:
			if segment.stime() < now - _MSG_TTL:
				self._sent.remove(segment)
		return True

	def _dispatch_message(self, addr, message):
		"""Send complete message data to the owner's data callback."""
		self._data_cb(addr, message, self._user_data)

	def _process_incoming(self, segment):
		"""Handle a new message segment.  First checks if there is only one
		segment to the message, and if the checksum from the header matches
		that computed from the data, dispatches it.  Otherwise, it adds the
		new segment to the list of other segments for that message, and 
		checks to see if the message is complete.  If all segments are present,
		the message is reassembled and dispatched."""

		string_sha = _stringify_sha(segment.master_sha())
		nsegs = segment.total_segments()
		addr = segment.addr()
		segno = segment.segment_number()

		# Short-circuit single-segment messages
		if segno == 1 and nsegs == 1:
			# Ensure the header's master sha actually equals the data's sha
			if string_sha == _stringify_sha(_sha_data(segment.data())):
				self._dispatch_message(addr, segment.data())
				return

		# Otherwise, track the new segment
		msg_seq_num = segment.message_sequence_number()
		msg_key = (addr[0], msg_seq_num, string_sha, nsegs)
		if not self._incoming.has_key(msg_key):
			self._incoming[msg_key] = {}

		# Look for a dupe, and if so, drop the new segment
		if self._incoming[msg_key].has_key(segno):
			return
		self._incoming[msg_key][segno] = segment

		# Dispatch the message if all segments are present and the sha is correct
		if len(self._incoming[msg_key]) == nsegs:
			all_data = ''
			for i in range(1, nsegs + 1):
				all_data = all_data + self._incoming[msg_key][i].data()
			if string_sha == _stringify_sha(_sha_data(all_data)):
				self._dispatch_message(addr, all_data)
			del self._incoming[msg_key]

	def _handle_incoming_data(self, source, condition):
		"""Handle incoming network data by making a message segment out of it
		sending it off to the processing function."""
		if not (condition & gobject.IO_IN):
			return True
		msg = {}
		data, addr = source.recvfrom(_MTU + _HEADER_LEN)
		try:
			segment = MessageSegment.new_from_data(addr, data)
			self._process_incoming(segment)
		except ValueError, exc:
			pass
		return True

	def send(self, data):
		"""Break data up into chunks and queue for later transmission."""
		if not self._started:
			raise Exception("Can't send anything until started!")

		self._seq_counter = self._seq_counter + 1
		if self._seq_counter > 65535:
			self._seq_counter = 1

		# Pack the data into network byte order
		template = "! %ds" % len(data)
		data = struct.pack(template, data)
		master_sha = _sha_data(data)

		# Split up the data into segments
		left = length = len(data)
		nmessages = length / _MTU
		if length % _MTU > 0:
			nmessages = nmessages + 1
		msg_num = 1
		while left > 0:
			msg = MessageSegment.new_from_parts(self._seq_counter, msg_num,
					nmessages, data[:_MTU], master_sha)
			self._outgoing.append(msg)
			msg_num = msg_num + 1
			data = data[_MTU:]
			left = left - _MTU
		if len(self._outgoing) > 0 and self._worker == 0:
			self._worker = gobject.idle_add(self._send_worker)

	def _send_worker(self):
		"""Send all queued segments that have yet to be transmitted."""
		self._worker = 0
		for segment in self._outgoing:
			data = segment.segment()
			self._send_sock.sendto(data, (self._remote_addr, self._port))
		self._sent = self._outgoing
		self._outgoing = []
		return False


def got_data(addr, data, user_data=None):
	print "Data (%s): %s" % (addr, data)

def main():
	pipe = MostlyReliablePipe('', '224.0.0.222', 2293, got_data)
	pipe.start()
	pipe.send('The quick brown fox jumps over the lazy dog')
	gtk.main()


if __name__ == "__main__":
	main()

