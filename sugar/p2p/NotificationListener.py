from Service import Service
from sugar.p2p.Notifier import Notifier
import network

class NotificationListener:
	def __init__(self, group, name):
		service = group.get_service(name, Notifier.TYPE)
		print service.get_address()
		print service.get_port()
		server = network.GroupServer(service.get_address(),
									 service.get_port(),
									 self._recv_multicast)
		server.start()
		
		self._listeners = {}
	
	def add_listener(self, listener):
		self._listeners.add(listener)
	
	def _recv_multicast(self, msg):
		print 'Got message ' + msg
		for listener in self._listeners:
			listener(msg)
