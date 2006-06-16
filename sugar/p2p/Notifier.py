from sugar.p2p import network
from sugar.presence.Service import Service

class Notifier:
	def __init__(self, service):
		address = service.get_address()
		port = service.get_port()
		self._client = network.GroupClient(address, port)
		
	def notify(self, msg):
		self._client.send_msg(msg)
