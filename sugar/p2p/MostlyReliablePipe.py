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

	def new_from_data(addr, data):
		"""Static constructor for creation from a packed data stream."""

		if not addr or type(addr) != type(()):
			raise ValueError("Address must be a tuple.")
		if len(addr) != 2 or type(addr[0]) != type("") or type(addr[1]) != type(1):
			raise ValueError("Address format was invalid.")
		if addr[1] < 1 or addr[1] > 65535:
			raise ValueError("Address port was invalid.")

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

	def __init__(self, segno, total_segs, msg_seq_num, master_sha):
		"""Should not be called directly."""
		if segno != 1 or total_segs != 1:
			raise ValueError("Retransmission request messages must have only one segment.")

		SegmentBase.__init__(self, segno, total_segs, msg_seq_num, master_sha)
		self._type = SegmentBase._SEGMENT_TYPE_DATA

	def _make_rtms_data(rt_msg_seq_num, rt_master_sha, rt_segment_number):
		"""Pack retransmission request payload."""
		data = struct.pack(RetransmitSegment._RT_DATA_TEMPLATE, rt_msg_seq_num,
				rt_master_sha, rt_segment_number)
		return (data, _sha_data(data), struct.calcsize(RetransmitSegment._RT_DATA_TEMPLATE))
	_make_rtms_data = staticmethod(_make_rtms_data)

	def new_from_parts(msg_seq_num, rt_msg_seq_num, rt_master_sha, rt_segment_number):
		"""Static constructor for creation from individual attributes."""
		(data, data_sha, data_len) = segment._make_rtms_data()
		segment = RetransmitSegment(1, 1, msg_seq_num, data_sha)
		segment._data_len = data_len
		segment._data = data

		segment._rt_msg_seq_num = rt_msg_seq_num
		segment._rt_master_sha = rt_master_sha
		segment._rt_segment_number = rt_segment_number
		return segment
	new_from_parts = staticmethod(new_from_parts)

	def _unpack_data(self, stream, data_len):
		if data_len != struct.calcsize(self._RT_DATA_TEMPLATE):
			raise ValueError("Retransmission request data had invalid length.")
		self._data_len = data_len
		(rt_msg_seq_num, rt_master_sha, rt_seg_no) = struct.unpack(self._RT_DATA_TEMPLATE,
				stream.read(self._data_len))
		self._data = struct.pack(self._RT_DATA_TEMPLATE, rt_msg_seq_num,
				rt_master_sha, rt_seg_no)
		self._rt_msg_seq_num = rt_msg_seq_num
		self._rt_master_sha = rt_master_sha
		self._rt_segment_number = rt_seg_no

	def rt_msg_seq_num(self):
		return self._rt_msg_seq_num

	def rt_master_sha(self):
		return self._rt_master_sha

	def rt_segment_number(self):
		return self._rt_segment_number	


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
		self._worker = 0
		self._seq_counter = 0

		self._outgoing = []
		self._sent = {}

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
		gobject.timeout_add(self._SEGMENT_TTL * 1000, self._segment_ttl_worker)

		self._started = True

	def _segment_ttl_worker(self):
		"""Cull already-sent message segments that are past their TTL."""
		now = time.time()
		for segment in self._sent[:]:
			if segment.stime() < now - self._SEGMENT_TTL:
				self._sent.remove(segment)
		return True

	def _dispatch_message(self, addr, message):
		"""Send complete message data to the owner's data callback."""
		self._data_cb(addr, message, self._user_data)

	def _process_incoming_data(self, segment):
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

	_STD_RETRANSMIT_INTERVAL = 500  # 1/2 second (in milliseconds)
	def _calc_next_retransmit(self, segment, now):
		"""Calculate the next time (in seconds) that a packet can be retransmitted."""
		num_retrans = segment.transmits() - 1
		interval = num_retrans * self._STD_RETRANSMIT_INTERVAL
		randomness = num_retrans * random.randint(-4, 11)
		real_interval = max(self._STD_RETRANSMIT_INTERVAL, interval + randomness)
		return max(now, segment.last_transmit() + (real_interval * .001))

	def _segment_retransmit_cb(self, segment):
		"""Add a segment ot the outgoing queue and schedule its transmission."""
		del self._sent[key]
		self._outgoing.append(segment)
		self._schedule_send_worker()
		return False

	def _schedule_segment_retransmit(self, segment, when):
		"""Schedule retransmission of a segment if one is not already scheduled."""
		if segment.userdata:
			# Already scheduled for retransmit
			return

		if when == 0:
			# Immediate retransmission
			segment.userdata = gobject.idle_add(self._segment_retransmit_cb, segment)
		else:
			# convert time to milliseconds
			timeout = int((when - time.time()) * 1000)
			segment.userdata = gobject.timeout_add(timeout, self._segment_retransmit_cb,
				segment)

	def _process_retransmit_request(self, segment):
		"""Validate and process a retransmission request."""
		key = (segment.rt_msg_seq_num(), segment.rt_master_sha(), segment.rt_segment_number())
		if not self._sent.has_key(key):
			# Either we don't know about the segment, or it was already culled
			return

		# Calculate next retransmission time and schedule packet for retransmit
		segment = self._sent[key]
		now = time.time()
		next_retrans = self._calc_next_retransmit(segment, now)
		self._schedule_segment_retransmit(segment, next_retrans - now)

	def _handle_incoming_data(self, source, condition):
		"""Handle incoming network data by making a message segment out of it
		sending it off to the processing function."""
		if not (condition & gobject.IO_IN):
			return True
		msg = {}
		data, addr = source.recvfrom(self._UDP_MSG_SIZE)
		try:
			segment = SegmentBase.new_from_data(addr, data)
			stype = segment.segment_type()
			if stype == SegmentBase.type_data():
				self._process_incoming_data(segment)
			elif stype == SegmentBase.type_retransmit():
				self._process_retransmit_request(segment)
		except ValueError, exc:
			print "Bad segment: %s" % exc
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
		mtu = SegmentBase.mtu()
		nmessages = length / mtu
		if length % mtu > 0:
			nmessages = nmessages + 1
		msg_num = 1
		while left > 0:
			seg = DataSegment.new_from_parts(msg_num, nmessages,
					self._seq_counter, master_sha, data[:mtu])
			self._outgoing.append(seg)
			msg_num = msg_num + 1
			data = data[mtu:]
			left = left - mtu
		self._schedule_send_worker()

	def _schedule_send_worker(self):
		if len(self._outgoing) > 0 and self._worker == 0:
			self._worker = gobject.idle_add(self._send_worker)

	def _send_worker(self):
		"""Send all queued segments that have yet to be transmitted."""
		self._worker = 0
		for segment in self._outgoing:
			packet = segment.packetize()
			segment.inc_transmits()
			self._send_sock.sendto(packet, (self._remote_addr, self._port))
			segment.userdata = None  # Retransmission GSource
			key = (segment.message_sequence_number(), segment.master_sha(), segment.segment_number())
			self._sent[key] = segment
		self._outgoing = []
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
		assert not seg.addr(), "Segment address was not None after init."
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

		assert seg.addr() == self._DEF_ADDRESS, "Segment address did not match expected."
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



def main():
	suite = unittest.TestSuite()
	SegmentBaseInitTestCase.addToSuite(suite)
	DataSegmentTestCase.addToSuite(suite)
	SHAUtilsTestCase.addToSuite(suite)

	runner = unittest.TextTestRunner()
	runner.run(suite)



def got_data(addr, data, user_data=None):
	print "Data (%s): %s" % (addr, data)

def foobar():
	pipe = MostlyReliablePipe('', '224.0.0.222', 2293, got_data)
	pipe.start()
	pipe.send('The quick brown fox jumps over the lazy dog')
	try:
		gtk.main()
	except KeyboardInterrupt:
		pass


if __name__ == "__main__":
	main()

