import socket
import threading
import traceback
import select
import time
import gobject

class GroupChatController(object):

	_MAX_MSG_SIZE = 500

	def __init__(self, address, port, data_cb):
		self._address = address
		self._port = port
		self._data_cb = data_cb

		self._setup_sender()
		self._setup_listener()

	def _setup_sender(self):
		self._send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		# Make the socket multicast-aware, and set TTL.
		self._send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 20) # Change TTL (=20) to suit

	def _setup_listener(self):
		# Listener socket
		self._listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

		# Set some options to make it multicast-friendly
		self._listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		try:
			self._listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
		except:
			pass
		self._listen_sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_TTL, 20)
		self._listen_sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_LOOP, 1)

	def start(self):
		# Set some more multicast options
		self._listen_sock.bind(('', self._port))
		self._listen_sock.settimeout(2)
		intf = socket.gethostbyname(socket.gethostname())
		self._listen_sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF, socket.inet_aton(intf) + socket.inet_aton('0.0.0.0'))
		self._listen_sock.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(self._address) + socket.inet_aton('0.0.0.0'))

		# Watch the listener socket for data
		gobject.io_add_watch(self._listen_sock, gobject.IO_IN, self._handle_incoming_data)

	def _handle_incoming_data(self, source, condition):
		if not (condition & gobject.IO_IN):
			return
		msg = {}
		msg['data'], (msg['addr'], msg['port']) = source.recvfrom(self._MAX_MSG_SIZE)
		if self._data_cb:
			self._data_cb(msg)
		return True

	def send_msg(self, data):
		self._send_sock.sendto(data, (self._address, self._port))

