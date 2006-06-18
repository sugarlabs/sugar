import logging

from sugar.p2p.Notifier import Notifier
from sugar.p2p import network

class NotificationListener:
	def __init__(self, service):
		logging.debug('Start notification listener. Service %s, address %s, port %s' % (service.get_type(), service.get_address(), service.get_port()))
		server = network.GroupServer(service.get_address(),
									 service.get_port(),
									 self._recv_multicast)
		server.start()
		
		self._listeners = []
	
	def add_listener(self, listener):
		self._listeners.append(listener)
	
	def _recv_multicast(self, msg):
		for listener in self._listeners:
			listener(msg)
