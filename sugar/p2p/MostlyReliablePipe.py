import socket
import time
import sha
import struct
import StringIO
import binascii
import random

import pygtk
pygtk.require('2.0')
import gtk, gobject


def _stringify_sha(sha):
	print_sha = ""
	for char in sha:
		print_sha = print_sha + binascii.b2a_hex(char)
	return print_sha

def _sha_data(data):
	sha_hash = sha.new()
	sha_hash.update(data)
	return sha_hash.digest()

_UDP_DATAGRAM_SIZE = 512

class SegmentBase(object):
	_MAGIC = 0xbaea4304

	# 4: magic (0xbaea4304)
	# 1: type
	# 2: segment number
	# 2: total segments
	# 2: message sequence number
	#20: total data sha1
	_HEADER_TEMPLATE = "! IbHHH20s"
	_HEADER_LEN = struct.calcsize(_HEADER_TEMPLATE)
	_MTU = _UDP_DATAGRAM_SIZE - _HEADER_LEN

	# Message segment packet types
	_SEGMENT_TYPE_DATA = 0
	_SEGMENT_TYPE_RETRANSMIT = 1

	def magic():
		return SegmentBase._MAGIC
	magic = staticmethod(magic)

	def header_template():
		return SegmentBase._HEADER_TEMPLATE
	header_template = staticmethod(header_template)

	def type_data():
		return SegmentBase._SEGMENT_TYPE_DATA
	type_data = staticmethod(type_data)

	def type_retransmit():
		return SegmentBase._SEGMENT_TYPE_RETRANSMIT
	type_retransmit = staticmethod(type_retransmit)

	def header_len():
		"""Return the header size of SegmentBase packets."""
		return SegmentBase._HEADER_LEN
	header_len = staticmethod(header_len)

	def mtu():
		"""Return the SegmentBase packet MTU."""
		return SegmentBase._MTU
	mtu = staticmethod(mtu)

	def __init__(self, segno, total_segs, msg_seq_num, master_sha):
		self._type = None
		self._transmits = 0
		self._last_transmit = 0
		self._data = None
		self._data_len = 0
		self.userdata = None
		self._stime = time.time()
		self._addr = None

		# Sanity checks on the message attributes
		if not segno or type(segno) != type(1):
			raise ValueError("Segment number must be in integer.")
		if segno < 1 or segno > 65535:
			raise ValueError("Segment number must be between 1 and 65535 inclusive.")
		if not total_segs or type(total_segs) != type(1):
			raise ValueError("Message segment total must be an integer.")
		if total_segs < 1 or total_segs > 65535:
			raise ValueError("Message must have between 1 and 65535 segments inclusive.")
		if segno > total_segs:
			raise ValueError("Segment number cannot be larger than message segment total.")
		if not msg_seq_num or type(msg_seq_num) != type(1):
			raise ValueError("Message sequnce number must be an integer.")
		if msg_seq_num < 1 or msg_seq_num > 65535:
			raise ValueError("Message sequence number must be between 1 and 65535 inclusive.")
		if not master_sha or type(master_sha) != type("") or len(master_sha) != 20:
			raise ValueError("Message SHA1 checksum invalid.")

		self._segno = segno
		self._total_segs = total_segs
		self._msg_seq_num = msg_seq_num
		self._master_sha = master_sha

	def _validate_address(addr):
		if not addr or type(addr) != type(()):
			raise ValueError("Address must be a tuple.")
		if len(addr) != 2 or type(addr[0]) != type("") or type(addr[1]) != type(1):
			raise ValueError("Address format was invalid.")
		if addr[1] < 1 or addr[1] > 65535:
			raise ValueError("Address port was invalid.")
	_validate_address = staticmethod(_validate_address)

	def new_from_data(addr, data):
		"""Static constructor for creation from a packed data stream."""
		SegmentBase._validate_address(addr)

		# Verify minimum length
		if not data:
			raise ValueError("Segment data is invalid.")
		data_len = len(data)
		if data_len < SegmentBase.header_len() + 1:
			raise ValueError("Segment is less then minimum required length")
		if data_len > _UDP_DATAGRAM_SIZE:
			raise ValueError("Segment data is larger than allowed.")
		stream = StringIO.StringIO(data)

		# Determine and verify the length of included data
		stream.seek(0, 2)
		data_len = stream.tell() - SegmentBase._HEADER_LEN
		stream.seek(0)

		if data_len < 1:
			raise ValueError("Segment must have some data.")
		if data_len > SegmentBase._MTU:
			raise ValueError("Data length must not be larger than the MTU (%s)." % SegmentBase._MTU)

		# Read the first header attributes
		(magic, seg_type, segno, total_segs, msg_seq_num, master_sha) = struct.unpack(SegmentBase._HEADER_TEMPLATE,
				stream.read(SegmentBase._HEADER_LEN))

		# Sanity checks on the message attributes
		if magic != SegmentBase._MAGIC:
			raise ValueError("Segment does not have the correct magic.")

		# if the segment is the only one in the message, validate the data
		if segno == 1 and total_segs == 1:
			data_sha = _sha_data(stream.read(data_len))
			if data_sha != master_sha:
				raise ValueError("Single segment message SHA checksums didn't match.")
			stream.seek(SegmentBase._HEADER_LEN)

		if seg_type == SegmentBase._SEGMENT_TYPE_DATA:
			segment = DataSegment(segno, total_segs, msg_seq_num, master_sha)
		elif seg_type == SegmentBase._SEGMENT_TYPE_RETRANSMIT:
			segment = RetransmitSegment(segno, total_segs, msg_seq_num, master_sha)
		else:
			raise ValueError("Segment has invalid type.")

		# Segment specific data interpretation
		segment._addr = addr
		segment._unpack_data(stream, data_len)

		return segment
	new_from_data = staticmethod(new_from_data)

	def stime(self):
		return self._stime

	def address(self):
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

	def segment_type(self):
		return self._type

	def packetize(self):
		"""Return a correctly formatted message that can be immediately sent."""
		header = struct.pack(self._HEADER_TEMPLATE, self._MAGIC, self._type,
				self._segno, self._total_segs, self._msg_seq_num, self._master_sha)
		return header + self._data

	def transmits(self):
		return self._transmits

	def inc_transmits(self):
		self._transmits = self._transmits + 1
		self._last_transmit = time.time()

	def last_transmit(self):
		return self._last_transmit

class DataSegment(SegmentBase):
	"""A message segment that encapsulates random data."""

	def __init__(self, segno, total_segs, msg_seq_num, master_sha):
		SegmentBase.__init__(self, segno, total_segs, msg_seq_num, master_sha)
		self._type = SegmentBase._SEGMENT_TYPE_DATA

	def _get_template_for_len(length):
		return "! %ds" % length
	_get_template_for_len = staticmethod(_get_template_for_len)

	def _unpack_data(self, stream, data_len):
		"""Unpack the data stream, called by constructor."""
		self._data_len = data_len
		template = DataSegment._get_template_for_len(self._data_len)
		self._data = struct.unpack(template, stream.read(self._data_len))[0]

	def new_from_parts(segno, total_segs, msg_seq_num, master_sha, data):
		"""Construct a new message segment from individual attributes."""
		if not data:
			raise ValueError("Must have valid data.")
		segment = DataSegment(segno, total_segs, msg_seq_num, master_sha)
		segment._data_len = len(data)
		template = DataSegment._get_template_for_len(segment._data_len)
		segment._data = struct.pack(template, data)
		return segment
	new_from_parts = staticmethod(new_from_parts)


class RetransmitSegment(SegmentBase):
	"""A message segment that encapsulates a retransmission request."""

	# Retransmission data format:
	#  2: message sequence number
	# 20: total data sha1
	#  2: segment number
	_RT_DATA_TEMPLATE = "! H20sH"
	_RT_DATA_LEN = struct.calcsize(_RT_DATA_TEMPLATE)

	def data_template():
		return RetransmitSegment._RT_DATA_TEMPLATE
	data_template = staticmethod(data_template)

	def __init__(self, segno, total_segs, msg_seq_num, master_sha):
		"""Should not be called directly."""
		if segno != 1 or total_segs != 1:
			raise ValueError("Retransmission request messages must have only one segment.")

		SegmentBase.__init__(self, segno, total_segs, msg_seq_num, master_sha)
		self._type = SegmentBase._SEGMENT_TYPE_RETRANSMIT

	def _verify_data(rt_msg_seq_num, rt_master_sha, rt_segment_number):
		# Sanity checks on the message attributes
		if not rt_segment_number or type(rt_segment_number) != type(1):
			raise ValueError("RT Segment number must be in integer.")
		if rt_segment_number < 1 or rt_segment_number > 65535:
			raise ValueError("RT Segment number must be between 1 and 65535 inclusive.")
		if not rt_msg_seq_num or type(rt_msg_seq_num) != type(1):
			raise ValueError("RT Message sequnce number must be an integer.")
		if rt_msg_seq_num < 1 or rt_msg_seq_num > 65535:
			raise ValueError("RT Message sequence number must be between 1 and 65535 inclusive.")
		if not rt_master_sha or type(rt_master_sha) != type("") or len(rt_master_sha) != 20:
			raise ValueError("RT Message SHA1 checksum invalid.")
	_verify_data = staticmethod(_verify_data)

	def _make_rtms_data(rt_msg_seq_num, rt_master_sha, rt_segment_number):
		"""Pack retransmission request payload."""
		data = struct.pack(RetransmitSegment._RT_DATA_TEMPLATE, rt_msg_seq_num,
				rt_master_sha, rt_segment_number)
		return (data, _sha_data(data))
	_make_rtms_data = staticmethod(_make_rtms_data)

	def new_from_parts(addr, msg_seq_num, rt_msg_seq_num, rt_master_sha, rt_segment_number):
		"""Static constructor for creation from individual attributes."""

		RetransmitSegment._verify_data(rt_msg_seq_num, rt_master_sha, rt_segment_number)
		(data, data_sha) = RetransmitSegment._make_rtms_data(rt_msg_seq_num,
				rt_master_sha, rt_segment_number)
		segment = RetransmitSegment(1, 1, msg_seq_num, data_sha)
		segment._data_len = RetransmitSegment._RT_DATA_LEN
		segment._data = data
		SegmentBase._validate_address(addr)
		segment._addr = addr

		segment._rt_msg_seq_num = rt_msg_seq_num
		segment._rt_master_sha = rt_master_sha
		segment._rt_segment_number = rt_segment_number
		return segment
	new_from_parts = staticmethod(new_from_parts)

	def _unpack_data(self, stream, data_len):
		if data_len != self._RT_DATA_LEN:
			raise ValueError("Retransmission request data had invalid length.")
		data = stream.read(data_len)
		(rt_msg_seq_num, rt_master_sha, rt_seg_no) = struct.unpack(self._RT_DATA_TEMPLATE, data)
		RetransmitSegment._verify_data(rt_msg_seq_num, rt_master_sha, rt_seg_no)

		self._data = data
		self._data_len = data_len
		self._rt_msg_seq_num = rt_msg_seq_num
		self._rt_master_sha = rt_master_sha
		self._rt_segment_number = rt_seg_no

	def rt_msg_seq_num(self):
		return self._rt_msg_seq_num

	def rt_master_sha(self):
		return self._rt_master_sha

	def rt_segment_number(self):
		return self._rt_segment_number	


class Message(object):
	"""Tracks an entire message object, which is composed of a number
	of individual segments."""
	def __init__(self, src_addr, msg_seq_num, msg_sha, total_segments):
		self._rt_target = 0
		self._next_rt_time = 0
		self._last_incoming_time = 0
		self._segments = {}
		self._complete = False
		self._dispatched_time = 0
		self._data = None
		self._data_sha = None
		self._src_addr = src_addr
		self._msg_seq_num = msg_seq_num
		self._msg_sha = msg_sha
		self._total_segments = total_segments
		self._rt_tries = {}
		for i in range(1, self._total_segments + 1):
			self._rt_tries[i] = 0

	def __del__(self):
		self.clear()

	def sha(self):
		return self._msg_sha

	def source_address(self):
		return self._src_addr

	def clear(self):
		for key in self._segments.keys()[:]:
			del self._segments[key]
			del self._rt_tries[key]
		self._segments = {}
		self._rt_tries = {}

	def has_segment(self, segno):
		return self._segments.has_key(segno)

	def first_missing(self):
		for i in range(1, self._total_segments + 1):
			if not self._segments.has_key(i):
				return i
		return 0

	_DEF_RT_REQUEST_INTERVAL = 0.09 # 70ms (in seconds)
	def update_rt_wait(self, now):
		"""now argument should be in seconds."""
		wait = self._DEF_RT_REQUEST_INTERVAL
		if self._last_incoming_time > now - 0.02:
			msg_completeness = float(len(self._segments)) / float(self._total_segments)
			wait = wait + (self._DEF_RT_REQUEST_INTERVAL * (1.0 - msg_completeness))
		self._next_rt_time = now + wait

	def add_segment(self, segment):
		if self.complete():
			return
		segno = segment.segment_number()
		if self._segments.has_key(segno):
			return
		self._segments[segno] = segment
		self._rt_tries[segno] = 0
		now = time.time()
		self._last_incoming_time = now

		num_segs = len(self._segments)
		if num_segs == self._total_segments:
			self._complete = True
			self._next_rt_time = 0
			self._data = ''
			for seg in self._segments.values():
				self._data = self._data + seg.data()
			self._data_sha = _sha_data(self._data)
		elif segno == num_segs or num_segs == 1:
			# If we're not missing segments, push back retransmit request
			self.update_rt_wait(now)

	def get_retransmit_message(self, msg_seq_num, segno):
		if segno < 1 or segno > self._total_segments:
			return None
		seg = RetransmitSegment.new_from_parts(self._src_addr, msg_seq_num,
				self._msg_seq_num, self._msg_sha, segno)
		self._rt_tries[segno] = self._rt_tries[segno] + 1
		self.update_rt_wait(time.time())
		return seg

	def complete(self):
		return self._complete

	def dispatch_time(self):
		return self._dispatch_time

	def set_dispatch_time(self):
		self._dispatch_time = time.time()

	def data(self):
		return (self._data, self._data_sha)

	def last_incoming_time(self):
		return self._last_incoming_time

	def next_rt_time(self):
		return self._next_rt_time

	def rt_tries(self, segno):
		if self._rt_tries.has_key(segno):
			return self._rt_tries[segno]
		return 0


class MostlyReliablePipe(object):
	"""Implement Mostly-Reliable UDP.  We don't actually care about guaranteeing
	delivery or receipt, just a better effort than no effort at all."""

	_UDP_MSG_SIZE = SegmentBase.mtu() + SegmentBase.header_len()
	_SEGMENT_TTL = 120 # 2 minutes

	def __init__(self, local_addr, remote_addr, port, data_cb, user_data=None):
		self._local_addr = local_addr
		self._remote_addr = remote_addr
		self._port = port
		self._data_cb = data_cb
		self._user_data = user_data
		self._started = False
		self._send_worker = 0
		self._seq_counter = 0
		self._drop_prob = 0
		self._rt_check_worker = 0

		self._outgoing = []
		self._sent = {}

		self._incoming = {}  # (message sha, # of segments) -> [segment1, segment2, ...]
		self._dispatched = {}

		self._setup_listener()
		self._setup_sender()

	def __del__(self):
		if self._send_worker > 0:
			gobject.source_remove(self._send_worker)
			self._send_worker = 0
		if self._rt_check_worker > 0:
			gobject.source_remove(self._rt_check_worker)
			self._rt_check_worker = 0

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
		self._listen_sock.bind((self._local_addr, self._port))
		self._listen_sock.settimeout(2)
		intf = socket.gethostbyname(socket.gethostname())
		self._listen_sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF,
				socket.inet_aton(intf) + socket.inet_aton('0.0.0.0'))
		self._listen_sock.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP,
				socket.inet_aton(self._remote_addr) + socket.inet_aton('0.0.0.0'))

		# Watch the listener socket for data
		gobject.io_add_watch(self._listen_sock, gobject.IO_IN, self._handle_incoming_data)
		gobject.timeout_add(self._SEGMENT_TTL * 1000, self._segment_ttl_worker)
		gobject.timeout_add(50, self._retransmit_check_worker)

		self._started = True

	def _segment_ttl_worker(self):
		"""Cull already-sent message segments that are past their TTL."""
		now = time.time()
		for key in self._sent.keys()[:]:
			segment = self._sent[key]
			if segment.stime() < now - self._SEGMENT_TTL:
				if segment.userdata:
					gobject.source_remove(segment.userdata)
				del self._sent[key]

		# Cull incomplete incoming segment chains that haven't gotten any data
		# for a long time either
		for msg_key in self._incoming.keys()[:]:
			message = self._incoming[msg_key]
			if message.last_incoming_time() < now - self._SEGMENT_TTL:
				del self._incoming[msg_key]

		# Remove already dispatched messages after a while
		for msg_key in self._dispatched.keys()[:]:
			message = self._dispatched[msg_key]
			if message.dispatch_time() < now - (self._SEGMENT_TTL*2):
				del self._dispatched[msg_key]

		return True

	_MAX_SEGMENT_RETRIES = 10
	def _retransmit_request(self, message):
		"""Returns true if the message has exceeded it's retry limit."""
		first_missing = message.first_missing()
		if first_missing > 0:
			num_retries = message.rt_tries(first_missing)
			if num_retries > self._MAX_SEGMENT_RETRIES:
				return True
			msg_seq = self._next_msg_seq()
			seg = message.get_retransmit_message(msg_seq, first_missing)
			if seg:
				print "(MRP): Requesting retransmit of %d by %s" % (first_missing, message.source_address())
				self._outgoing.append(seg)
				self._schedule_send_worker()
		return False

	def _retransmit_check_worker(self):
		try:
			now = time.time()
			for key in self._incoming.keys()[:]:
				message = self._incoming[key]
				if message.complete():
					continue
				next_rt = message.next_rt_time()
				if next_rt == 0 or next_rt > now:
					continue
				if self._retransmit_request(message):
					# Kill the message, too many retries
					print "(MRP): Dropped message %s, exceeded retries." % _stringify_sha(message.sha())
					self._dispatched[key] = message
					message.set_dispatch_time()
					del self._incoming[key]
		except KeyboardInterrupt:
			return False
		return True

	def _process_incoming_data(self, segment):
		"""Handle a new message segment.  First checks if there is only one
		segment to the message, and if the checksum from the header matches
		that computed from the data, dispatches it.  Otherwise, it adds the
		new segment to the list of other segments for that message, and 
		checks to see if the message is complete.  If all segments are present,
		the message is reassembled and dispatched."""

		msg_sha = segment.master_sha()
		nsegs = segment.total_segments()
		addr = segment.address()
		segno = segment.segment_number()

		msg_seq_num = segment.message_sequence_number()
		msg_key = (addr[0], msg_seq_num, msg_sha, nsegs)

		if self._dispatched.has_key(msg_key):
			# We already dispatched this message, this segment is useless
			return
		# First segment in the message
		if not self._incoming.has_key(msg_key):
			self._incoming[msg_key] = Message((addr[0], self._port), msg_seq_num, msg_sha, nsegs)

		message = self._incoming[msg_key]
		# Look for a dupe, and if so, drop the new segment
		if message.has_segment(segno):
			return
		message.add_segment(segment)

		# Dispatch the message if all segments are present and the sha is correct
		if message.complete():
			(msg_data, complete_data_sha) = message.data()
			if msg_sha == complete_data_sha:
				self._data_cb(addr, msg_data, self._user_data)
			self._dispatched[msg_key] = message
			message.set_dispatch_time()
			del self._incoming[msg_key]
			return

	def _segment_retransmit_cb(self, key, segment):
		"""Add a segment ot the outgoing queue and schedule its transmission."""
		del self._sent[key]
		self._outgoing.append(segment)
		self._schedule_send_worker()
		return False

	def _schedule_segment_retransmit(self, key, segment, when, now):
		"""Schedule retransmission of a segment if one is not already scheduled."""
		if segment.userdata:
			# Already scheduled for retransmit
			return

		if when <= now:
			# Immediate retransmission
			self._segment_retransmit_cb(key, segment)
		else:
			# convert time to milliseconds
			timeout = int((when - now) * 1000)
			segment.userdata = gobject.timeout_add(timeout, self._segment_retransmit_cb,
				key, segment)

	_STD_RETRANSMIT_INTERVAL = 0.05  # 50ms (in seconds)
	def _process_retransmit_request(self, segment):
		"""Validate and process a retransmission request."""
		key = (segment.rt_msg_seq_num(), segment.rt_master_sha(), segment.rt_segment_number())
		if not self._sent.has_key(key):
			# Either we don't know about the segment, or it was already culled
			return

		# Calculate next retransmission time and schedule packet for retransmit
		segment = self._sent[key]
		# only retransmit segments every 150ms or more
		now = time.time()
		next_transmit = max(now, segment.last_transmit() + self._STD_RETRANSMIT_INTERVAL)
		self._schedule_segment_retransmit(key, segment, next_transmit, now)

	def set_drop_probability(self, prob=4):
		"""Debugging function to randomly drop incoming packets.
		The prob argument should be an integer between 1 and 10 to drop,
		or 0 to drop none.  Higher numbers drop more packets."""
		self._drop_prob = prob

	def _handle_incoming_data(self, source, condition):
		"""Handle incoming network data by making a message segment out of it
		sending it off to the processing function."""
		if not (condition & gobject.IO_IN):
			return True
		msg = {}
		data, addr = source.recvfrom(self._UDP_MSG_SIZE)

		should_drop = False
		p = random.random() * 10.0
		if self._drop_prob > 0 and p <= self._drop_prob:
			should_drop = True

		try:
			segment = SegmentBase.new_from_data(addr, data)
			if should_drop:
				print "(MRP): Dropped segment %d." % segment.segment_number()
			else:
				stype = segment.segment_type()
				if stype == SegmentBase.type_data():
					self._process_incoming_data(segment)
				elif stype == SegmentBase.type_retransmit():
					self._process_retransmit_request(segment)
		except ValueError, exc:
			print "(MRP): Bad segment: %s" % exc
		return True

	def _next_msg_seq(self):
		self._seq_counter = self._seq_counter + 1
		if self._seq_counter > 65535:
			self._seq_counter = 1
		return self._seq_counter

	def send(self, data):
		"""Break data up into chunks and queue for later transmission."""
		if not self._started:
			raise Exception("Can't send anything until started!")

		msg_seq = self._next_msg_seq()

		# Pack the data into network byte order
		template = "! %ds" % len(data)
		data = struct.pack(template, data)
		master_sha = _sha_data(data)

		# Split up the data into segments
		left = length = len(data)
		mtu = SegmentBase.mtu()
		nmessages = length / mtu
		if length % mtu > 0:
			nmessages = nmessages + 1
		msg_num = 1
		while left > 0:
			seg = DataSegment.new_from_parts(msg_num, nmessages,
					msg_seq, master_sha, data[:mtu])
			self._outgoing.append(seg)
			msg_num = msg_num + 1
			data = data[mtu:]
			left = left - mtu
		self._schedule_send_worker()

	def _schedule_send_worker(self):
		if len(self._outgoing) > 0 and self._send_worker == 0:
			self._send_worker = gobject.timeout_add(50, self._send_worker_cb)

	def _send_worker_cb(self):
		"""Send all queued segments that have yet to be transmitted."""
		self._send_worker = 0
		nsent = 0
		for segment in self._outgoing:
			packet = segment.packetize()
			segment.inc_transmits()
			addr = (self._remote_addr, self._port)
			if segment.address():
				addr = segment.address()
			self._send_sock.sendto(packet, addr)
			if segment.userdata:
				gobject.source_remove(segment.userdata)
			segment.userdata = None  # Retransmission GSource
			key = (segment.message_sequence_number(), segment.master_sha(), segment.segment_number())
			self._sent[key] = segment
			nsent = nsent + 1
			if nsent > 10:
				break
		self._outgoing = self._outgoing[nsent:]
		if len(self._outgoing):
			self._schedule_send_worker()
		return False


#################################################################
# Tests
#################################################################

import unittest


class SegmentBaseTestCase(unittest.TestCase):
	_DEF_SEGNO = 1
	_DEF_TOT_SEGS = 5
	_DEF_MSG_SEQ_NUM = 4556
	_DEF_MASTER_SHA = "12345678901234567890"
	_DEF_SEG_TYPE = 0

	_DEF_ADDRESS = ('123.3.2.1', 3333)
	_SEG_MAGIC = 0xbaea4304


class SegmentBaseInitTestCase(SegmentBaseTestCase):
	def _test_init_fail(self, segno, total_segs, msg_seq_num, master_sha, fail_msg):
		try:
			seg = SegmentBase(segno, total_segs, msg_seq_num, master_sha)
		except ValueError, exc:
			pass
		else:
			self.fail("expected a ValueError for %s." % fail_msg)

	def testSegmentBase(self):
		assert SegmentBase.magic() == self._SEG_MAGIC, "Segment magic wasn't correct!"
		assert SegmentBase.header_len() > 0, "header size was not greater than zero."
		assert SegmentBase.mtu() > 0, "MTU was not greater than zero."
		assert SegmentBase.mtu() + SegmentBase.header_len() == _UDP_DATAGRAM_SIZE, "MTU + header size didn't equal expected %d." % _UDP_DATAGRAM_SIZE

	def testGoodInit(self):
		seg = SegmentBase(self._DEF_SEGNO, self._DEF_TOT_SEGS, self._DEF_MSG_SEQ_NUM, self._DEF_MASTER_SHA)
		assert seg.stime() < time.time(), "segment start time is less than now!"
		assert not seg.address(), "Segment address was not None after init."
		assert seg.segment_number() == self._DEF_SEGNO, "Segment number wasn't correct after init."
		assert seg.total_segments() == self._DEF_TOT_SEGS, "Total segments wasn't correct after init."
		assert seg.message_sequence_number() == self._DEF_MSG_SEQ_NUM, "Message sequence number wasn't correct after init."
		assert seg.master_sha() == self._DEF_MASTER_SHA, "Message master SHA wasn't correct after init."
		assert seg.segment_type() == None, "Segment type was not None after init."
		assert seg.transmits() == 0, "Segment transmits was not 0 after init."
		assert seg.last_transmit() == 0, "Segment last transmit was  not 0 after init."
		assert seg.data() == None, "Segment data was not None after init."

	def testSegmentNumber(self):
		self._test_init_fail(0, self._DEF_TOT_SEGS, self._DEF_MSG_SEQ_NUM, self._DEF_MASTER_SHA, "invalid segment number")
		self._test_init_fail(65536, self._DEF_TOT_SEGS, self._DEF_MSG_SEQ_NUM, self._DEF_MASTER_SHA, "invalid segment number")
		self._test_init_fail(None, self._DEF_TOT_SEGS, self._DEF_MSG_SEQ_NUM, self._DEF_MASTER_SHA, "invalid segment number")
		self._test_init_fail("", self._DEF_TOT_SEGS, self._DEF_MSG_SEQ_NUM, self._DEF_MASTER_SHA, "invalid segment number")

	def testTotalMessageSegmentNumber(self):
		self._test_init_fail(self._DEF_SEGNO, 0, self._DEF_MSG_SEQ_NUM, self._DEF_MASTER_SHA, "invalid total segments")
		self._test_init_fail(self._DEF_SEGNO, 65536, self._DEF_MSG_SEQ_NUM, self._DEF_MASTER_SHA, "invalid total segments")
		self._test_init_fail(self._DEF_SEGNO, None, self._DEF_MSG_SEQ_NUM, self._DEF_MASTER_SHA, "invalid total segments")
		self._test_init_fail(self._DEF_SEGNO, "", self._DEF_MSG_SEQ_NUM, self._DEF_MASTER_SHA, "invalid total segments")

	def testMessageSequenceNumber(self):
		self._test_init_fail(self._DEF_SEGNO, self._DEF_TOT_SEGS, 0, self._DEF_MASTER_SHA, "invalid message sequence number")
		self._test_init_fail(self._DEF_SEGNO, self._DEF_TOT_SEGS, 65536, self._DEF_MASTER_SHA, "invalid message sequence number")
		self._test_init_fail(self._DEF_SEGNO, self._DEF_TOT_SEGS, None, self._DEF_MASTER_SHA, "invalid message sequence number")
		self._test_init_fail(self._DEF_SEGNO, self._DEF_TOT_SEGS, "", self._DEF_MASTER_SHA, "invalid message sequence number")

	def testMasterSHA(self):
		self._test_init_fail(self._DEF_SEGNO, self._DEF_TOT_SEGS, self._DEF_MSG_SEQ_NUM, "1" * 19, "invalid SHA1 data hash")
		self._test_init_fail(self._DEF_SEGNO, self._DEF_TOT_SEGS, self._DEF_MSG_SEQ_NUM, "1" * 21, "invalid SHA1 data hash")
		self._test_init_fail(self._DEF_SEGNO, self._DEF_TOT_SEGS, self._DEF_MSG_SEQ_NUM, None, "invalid SHA1 data hash")
		self._test_init_fail(self._DEF_SEGNO, self._DEF_TOT_SEGS, self._DEF_MSG_SEQ_NUM, 1234, "invalid SHA1 data hash")

	def _testNewFromDataFail(self, addr, data, fail_msg):
		try:
			seg = SegmentBase.new_from_data(addr, data)
		except ValueError, exc:
			pass
		else:
			self.fail("expected a ValueError about %s." % fail_msg)

	def testNewFromDataAddress(self):
		self._testNewFromDataFail(None, None, "bad address")
		self._testNewFromDataFail('', None, "bad address")
		self._testNewFromDataFail((''), None, "bad address")
		self._testNewFromDataFail((1), None, "bad address")
		self._testNewFromDataFail(('', ''), None, "bad address")
		self._testNewFromDataFail((1, 3333), None, "bad address")
		self._testNewFromDataFail(('', 0), None, "bad address")
		self._testNewFromDataFail(('', 65536), None, "bad address")

	def testNewFromDataData(self):
		"""Only test generic new_from_data() bits, not type-specific ones."""
		self._testNewFromDataFail(self._DEF_ADDRESS, None, "invalid data")

		really_short_data = "111"
		self._testNewFromDataFail(self._DEF_ADDRESS, really_short_data, "data too short")

		only_header_data = "1" * SegmentBase.header_len()
		self._testNewFromDataFail(self._DEF_ADDRESS, only_header_data, "data too short")

		too_much_data = "1" * (_UDP_DATAGRAM_SIZE + 1)
		self._testNewFromDataFail(self._DEF_ADDRESS, too_much_data, "too much data")

		header_template = SegmentBase.header_template()
		bad_magic_data = struct.pack(header_template, 0x12345678, self._DEF_SEG_TYPE, 
				self._DEF_SEGNO, self._DEF_TOT_SEGS, self._DEF_MSG_SEQ_NUM, self._DEF_MASTER_SHA)
		self._testNewFromDataFail(self._DEF_ADDRESS, bad_magic_data, "invalid magic")

		bad_type_data = struct.pack(header_template, self._SEG_MAGIC, -1, self._DEF_SEGNO,
				self._DEF_TOT_SEGS, self._DEF_MSG_SEQ_NUM, self._DEF_MASTER_SHA)
		self._testNewFromDataFail(self._DEF_ADDRESS, bad_type_data, "invalid segment type")

		# Test master_sha that doesn't match data's SHA
		header = struct.pack(header_template, self._SEG_MAGIC, self._DEF_SEG_TYPE, 1, 1,
				self._DEF_MSG_SEQ_NUM, self._DEF_MASTER_SHA)
		data = struct.pack("! 15s", "7" * 15)
		self._testNewFromDataFail(self._DEF_ADDRESS, header + data, "single-segment message SHA mismatch")

	def addToSuite(suite):
		suite.addTest(SegmentBaseInitTestCase("testGoodInit"))
		suite.addTest(SegmentBaseInitTestCase("testSegmentNumber"))
		suite.addTest(SegmentBaseInitTestCase("testTotalMessageSegmentNumber"))
		suite.addTest(SegmentBaseInitTestCase("testMessageSequenceNumber"))
		suite.addTest(SegmentBaseInitTestCase("testMasterSHA"))
		suite.addTest(SegmentBaseInitTestCase("testNewFromDataAddress"))
		suite.addTest(SegmentBaseInitTestCase("testNewFromDataData"))
	addToSuite = staticmethod(addToSuite)


class DataSegmentTestCase(SegmentBaseTestCase):
	"""Test DataSegment class specific initialization and stuff."""

	def testInit(self):
		seg = DataSegment(self._DEF_SEGNO, self._DEF_TOT_SEGS, self._DEF_MSG_SEQ_NUM,
				self._DEF_MASTER_SHA)
		assert seg.segment_type() == SegmentBase.type_data(), "Segment wasn't a data segment."

	def testNewFromParts(self):
		try:
			seg = DataSegment.new_from_parts(self._DEF_SEGNO, self._DEF_TOT_SEGS,
					self._DEF_MSG_SEQ_NUM, self._DEF_MASTER_SHA, None)
		except ValueError, exc:
			pass
		else:
			self.fail("Expected ValueError about invalid data.")

		# Ensure message data is same as we stuff in after object is instantiated
		payload = "How are you today?"
		seg = DataSegment.new_from_parts(self._DEF_SEGNO, self._DEF_TOT_SEGS, self._DEF_MSG_SEQ_NUM,
				self._DEF_MASTER_SHA, payload)
		assert seg.data() == payload, "Data after segment creation didn't match expected."

	def testNewFromData(self):
		"""Test DataSegment's new_from_data() functionality."""

		# Make sure something valid actually works
		header_template = SegmentBase.header_template()
		payload_str = "How are you today?"
		payload = struct.pack("! %ds" % len(payload_str), payload_str)
		payload_sha = _sha_data(payload)
		header = struct.pack(header_template, self._SEG_MAGIC, SegmentBase.type_data(), self._DEF_SEGNO,
				self._DEF_TOT_SEGS, self._DEF_MSG_SEQ_NUM, payload_sha)
		seg = SegmentBase.new_from_data(self._DEF_ADDRESS, header + payload)

		assert seg.address() == self._DEF_ADDRESS, "Segment address did not match expected."
		assert seg.segment_type() == SegmentBase.type_data(), "Segment type did not match expected."
		assert seg.segment_number() == self._DEF_SEGNO, "Segment number did not match expected."
		assert seg.total_segments() == self._DEF_TOT_SEGS, "Total segments did not match expected."
		assert seg.message_sequence_number() == self._DEF_MSG_SEQ_NUM, "Message sequence number did not match expected."
		assert seg.master_sha() == payload_sha, "Message master SHA did not match expected."
		assert seg.data() == payload, "Segment data did not match expected payload."

	def addToSuite(suite):
		suite.addTest(DataSegmentTestCase("testInit"))
		suite.addTest(DataSegmentTestCase("testNewFromParts"))
		suite.addTest(DataSegmentTestCase("testNewFromData"))
	addToSuite = staticmethod(addToSuite)


class RetransmitSegmentTestCase(SegmentBaseTestCase):
	"""Test RetransmitSegment class specific initialization and stuff."""

	def _test_init_fail(self, segno, total_segs, msg_seq_num, master_sha, fail_msg):
		try:
			seg = RetransmitSegment(segno, total_segs, msg_seq_num, master_sha)
		except ValueError, exc:
			pass
		else:
			self.fail("expected a ValueError for %s." % fail_msg)

	def testInit(self):
		self._test_init_fail(0, 1, self._DEF_MSG_SEQ_NUM, self._DEF_MASTER_SHA, "invalid segment number")
		self._test_init_fail(2, 1, self._DEF_MSG_SEQ_NUM, self._DEF_MASTER_SHA, "invalid segment number")
		self._test_init_fail(1, 0, self._DEF_MSG_SEQ_NUM, self._DEF_MASTER_SHA, "invalid number of total segments")
		self._test_init_fail(1, 2, self._DEF_MSG_SEQ_NUM, self._DEF_MASTER_SHA, "invalid number of total segments")

		# Something that's supposed to work
		seg = RetransmitSegment(1, 1, self._DEF_MSG_SEQ_NUM, self._DEF_MASTER_SHA)
		assert seg.segment_type() == SegmentBase.type_retransmit(), "Segment wasn't a retransmit segment."

	def _test_new_from_parts_fail(self, msg_seq_num, rt_msg_seq_num, rt_master_sha, rt_segment_number, fail_msg):
		try:
			seg = RetransmitSegment.new_from_parts(self._DEF_ADDRESS, msg_seq_num, rt_msg_seq_num,
						rt_master_sha, rt_segment_number)
		except ValueError, exc:
			pass
		else:
			self.fail("expected a ValueError for %s." % fail_msg)

	def testNewFromParts(self):
		"""Test RetransmitSegment's new_from_parts() functionality."""
		self._test_new_from_parts_fail(0, self._DEF_MSG_SEQ_NUM, self._DEF_MASTER_SHA,
				self._DEF_SEGNO, "invalid message sequence number")
		self._test_new_from_parts_fail(65536, self._DEF_MSG_SEQ_NUM, self._DEF_MASTER_SHA,
				self._DEF_SEGNO, "invalid message sequence number")
		self._test_new_from_parts_fail(None, self._DEF_MSG_SEQ_NUM, self._DEF_MASTER_SHA,
				self._DEF_SEGNO, "invalid message sequence number")
		self._test_new_from_parts_fail("", self._DEF_MSG_SEQ_NUM, self._DEF_MASTER_SHA,
				self._DEF_SEGNO, "invalid message sequence number")

		self._test_new_from_parts_fail(self._DEF_MSG_SEQ_NUM, 0, self._DEF_MASTER_SHA,
				self._DEF_SEGNO, "invalid retransmit message sequence number")
		self._test_new_from_parts_fail(self._DEF_MSG_SEQ_NUM, 65536, self._DEF_MASTER_SHA,
				self._DEF_SEGNO, "invalid retransmit message sequence number")
		self._test_new_from_parts_fail(self._DEF_MSG_SEQ_NUM, None, self._DEF_MASTER_SHA,
				self._DEF_SEGNO, "invalid retransmit message sequence number")
		self._test_new_from_parts_fail(self._DEF_MSG_SEQ_NUM, "", self._DEF_MASTER_SHA,
				self._DEF_SEGNO, "invalid retransmit message sequence number")

		self._test_new_from_parts_fail(self._DEF_MSG_SEQ_NUM, self._DEF_MSG_SEQ_NUM, "1" * 19,
				self._DEF_SEGNO, "invalid retransmit message master SHA")
		self._test_new_from_parts_fail(self._DEF_MSG_SEQ_NUM, self._DEF_MSG_SEQ_NUM, "1" * 21,
				self._DEF_SEGNO, "invalid retransmit message master SHA")
		self._test_new_from_parts_fail(self._DEF_MSG_SEQ_NUM, self._DEF_MSG_SEQ_NUM, None,
				self._DEF_SEGNO, "invalid retransmit message master SHA")
		self._test_new_from_parts_fail(self._DEF_MSG_SEQ_NUM, self._DEF_MSG_SEQ_NUM, 1234,
				self._DEF_SEGNO, "invalid retransmit message master SHA")

		self._test_new_from_parts_fail(self._DEF_MSG_SEQ_NUM, self._DEF_MSG_SEQ_NUM,
				self._DEF_MASTER_SHA, 0, "invalid retransmit message segment number")
		self._test_new_from_parts_fail(self._DEF_MSG_SEQ_NUM, self._DEF_MSG_SEQ_NUM,
				self._DEF_MASTER_SHA, 65536, "invalid retransmit message segment number")
		self._test_new_from_parts_fail(self._DEF_MSG_SEQ_NUM, self._DEF_MSG_SEQ_NUM,
				self._DEF_MASTER_SHA, None, "invalid retransmit message segment number")
		self._test_new_from_parts_fail(self._DEF_MSG_SEQ_NUM, self._DEF_MSG_SEQ_NUM,
				self._DEF_MASTER_SHA, "", "invalid retransmit message segment number")

		# Ensure message data is same as we stuff in after object is instantiated
		seg = RetransmitSegment.new_from_parts(self._DEF_ADDRESS, self._DEF_MSG_SEQ_NUM, self._DEF_MSG_SEQ_NUM,
				self._DEF_MASTER_SHA, self._DEF_SEGNO)
		assert seg.rt_msg_seq_num() == self._DEF_MSG_SEQ_NUM, "RT message sequence number after segment creation didn't match expected."
		assert seg.rt_master_sha() == self._DEF_MASTER_SHA, "RT master SHA after segment creation didn't match expected."
		assert seg.rt_segment_number() == self._DEF_SEGNO, "RT segment number after segment creation didn't match expected."

	def _new_from_data(self, rt_msg_seq_num, rt_master_sha, rt_segment_number):
		payload = struct.pack(RetransmitSegment.data_template(), rt_msg_seq_num, rt_master_sha, rt_segment_number)
		payload_sha = _sha_data(payload)
		header_template = SegmentBase.header_template()
		header = struct.pack(header_template, self._SEG_MAGIC, SegmentBase.type_retransmit(), 1, 1,
				self._DEF_MSG_SEQ_NUM, payload_sha)
		return header + payload

	def _test_new_from_data_fail(self, rt_msg_seq_num, rt_master_sha, rt_segment_number, fail_msg):
		try:
			packet = self._new_from_data(rt_msg_seq_num, rt_master_sha, rt_segment_number)
			seg = SegmentBase.new_from_data(self._DEF_ADDRESS, packet)
		except ValueError, exc:
			pass
		else:
			self.fail("Expected a ValueError about %s." % fail_msg)

	def testNewFromData(self):
		"""Test DataSegment's new_from_data() functionality."""
		self._test_new_from_data_fail(0, self._DEF_MASTER_SHA, self._DEF_SEGNO, "invalid RT message sequence number")
		self._test_new_from_data_fail(65536, self._DEF_MASTER_SHA, self._DEF_SEGNO, "invalid RT message sequence number")
		
		self._test_new_from_data_fail(self._DEF_MSG_SEQ_NUM, self._DEF_MASTER_SHA, 0, "invalid RT segment number")
		self._test_new_from_data_fail(self._DEF_MSG_SEQ_NUM, self._DEF_MASTER_SHA, 65536, "invalid RT segment number")

		# Ensure something that should work
		packet = self._new_from_data(self._DEF_MSG_SEQ_NUM, self._DEF_MASTER_SHA, self._DEF_SEGNO)
		seg = SegmentBase.new_from_data(self._DEF_ADDRESS, packet)
		assert seg.segment_type() == SegmentBase.type_retransmit(), "Segment wasn't expected type."
		assert seg.rt_msg_seq_num() == self._DEF_MSG_SEQ_NUM, "Segment RT message sequence number didn't match expected."
		assert seg.rt_master_sha() == self._DEF_MASTER_SHA, "Segment RT master SHA didn't match expected."
		assert seg.rt_segment_number() == self._DEF_SEGNO, "Segment RT segment number didn't match expected."

	def testPartsToData(self):
		seg = RetransmitSegment.new_from_parts(self._DEF_ADDRESS, self._DEF_MSG_SEQ_NUM, self._DEF_MSG_SEQ_NUM,
				self._DEF_MASTER_SHA, self._DEF_SEGNO)
		new_seg = SegmentBase.new_from_data(self._DEF_ADDRESS, seg.packetize())
		assert new_seg.rt_msg_seq_num() == self._DEF_MSG_SEQ_NUM, "Segment RT message sequence number didn't match expected."
		assert new_seg.rt_master_sha() == self._DEF_MASTER_SHA, "Segment RT master SHA didn't match expected."
		assert new_seg.rt_segment_number() == self._DEF_SEGNO, "Segment RT segment number didn't match expected."

	def addToSuite(suite):
		suite.addTest(RetransmitSegmentTestCase("testInit"))
		suite.addTest(RetransmitSegmentTestCase("testNewFromParts"))
		suite.addTest(RetransmitSegmentTestCase("testNewFromData"))
		suite.addTest(RetransmitSegmentTestCase("testPartsToData"))
	addToSuite = staticmethod(addToSuite)


class SHAUtilsTestCase(unittest.TestCase):
	def testSHA(self):
		data = "235jklqt3hjwasdv879wfe89723rqjh32tr3hwaejksdvd89udsv89dsgiougjktqjhk23tjht23hjt3qhjewagthjasgdgsd"
		data_sha = _sha_data(data)
		assert len(data_sha) == 20, "SHA wasn't correct size."
		known_sha = "\xee\x9e\xb9\x1d\xe8\x96\x75\xcb\x12\xf1\x25\x22\x0f\x76\xf7\xf3\xc8\x4e\xbf\xcd"
		assert data_sha == known_sha, "SHA didn't match known SHA."

	def testStringifySHA(self):
		data = "jlkwjlkaegdjlksgdjklsdgajklganjtwn23n325n23tjwgeajkga nafDA fwqnjlqtjkl23tjk2365jlk235jkl2356jlktjkltewjlktewjklewtjklaggsda"
		data_known_sha = "9650c23db78092a0ffda4577c87ebf36d25c868e"
		assert _stringify_sha(_sha_data(data)) == data_known_sha, "SHA stringify didn't return correct SHA."
		# Do it twice for kicks
		assert _stringify_sha(_sha_data(data)) == data_known_sha, "SHA stringify didn't return correct SHA."

	def addToSuite(suite):
		suite.addTest(SHAUtilsTestCase("testSHA"))
		suite.addTest(SHAUtilsTestCase("testStringifySHA"))
	addToSuite = staticmethod(addToSuite)



def foobar():
	suite = unittest.TestSuite()
	SegmentBaseInitTestCase.addToSuite(suite)
	DataSegmentTestCase.addToSuite(suite)
	RetransmitSegmentTestCase.addToSuite(suite)
	SHAUtilsTestCase.addToSuite(suite)

	runner = unittest.TextTestRunner()
	runner.run(suite)



def got_data(addr, data, user_data=None):
	print "Got data from %s, writing to %s." % (addr, user_data)
	fl = open(user_data, "w+")
	fl.write(data)
	fl.close()	

def main():
	import sys
	pipe = MostlyReliablePipe('', '224.0.0.222', 2293, got_data, sys.argv[2])
#	pipe.set_drop_probability(4)
	pipe.start()
	fl = open(sys.argv[1], "r")
	data = fl.read()
	fl.close()
	msg = """The said Eliza, John, and Georgiana were now clustered round their mama in the drawing-room: 
she lay reclined on a sofa by the fireside, and with her darlings about her (for the time neither 
quarrelling nor crying) looked perfectly happy. Me, she had dispensed from joining the group; saying, 
'She regretted to be under the necessity of keeping me at a distance; but that until she heard from 
Bessie, and could discover by her own observation, that I was endeavouring in good earnest to acquire 
a more sociable and childlike disposition, a more attractive and sprightly manner -- something lighter, 
franker, more natural, as it were -- she really must exclude me from privileges intended only for
 contented, happy, little children.'"""
	pipe.send(data)
	try:
		gtk.main()
	except KeyboardInterrupt:
		pass


if __name__ == "__main__":
	main()

