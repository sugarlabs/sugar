import network

class Notifier:
	def __init__(self, group, name):
		service = group.get_service(name)
		address = service.get_address()
		port = service.get_port()
		self._client = network.GroupClient(address, port)
		
	def notify(self, msg):
		self._client.send_msg(msg)
