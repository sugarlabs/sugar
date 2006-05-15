from sugar.p2p.NotificationListener import NotificationListener
from sugar.p2p import network

class Notifier:
	TYPE = "_olpc_model_notification._udp"
	ADDRESS = "224.0.0.222"
	PORT = 6300
	
	def __init__(self, group, name):
		service = Service(name, NotificationListener.TYPE,
						  NotificationListener.ADDRESS,
						  NotificationListener.PORT, True)
		service.register(group)

		address = service.get_address()
		port = service.get_port()
		self._client = network.GroupClient(address, port)
		
	def notify(self, msg):
		self._client.send_msg(msg)
