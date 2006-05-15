from Service import Service
import network

class NotificationListener:
	TYPE = "_olpc_model_notification._udp"
	ADDRESS = "224.0.0.222"
	PORT = 6300
	
	def __init__(self, group, name):
		server = network.GroupServer(NotificationListener.TYPE,
									 NotificationListener.PORT,
									 self._recv_multicast)
		server.start()

		service = Service(name, NotificationListener.TYPE,
						  NotificationListener.ADDRESS,
						  NotificationListener.PORT, True)
		service.register(group)
		
		self._listeners = {}
	
	def add_listener(self, listener):
		self._listeners.add(listener)
	
	def _recv_multicast(self, msg):
		for listener in self._listeners:
			listener(msg)
