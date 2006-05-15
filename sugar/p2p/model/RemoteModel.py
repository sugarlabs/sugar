import xmlrpclib

from sugar.p2p.NotificationListener import NotificationListener
from sugar.p2p.model.AbstractModel import AbstractModel

class RemoteModel(AbstractModel):
	def __init__(self, group, service):
		AbstractModel.__init__(self)
		
		self._service = service
		self._group = group
		
		addr = "http://%s:%d" % (service.get_address(), service.get_port())
		self._client = xmlrpclib.ServerProxy(addr)
		
		self._setup_notification_listener()

	def get_value(self, key):
		return self._client.get_value(key)
		
	def set_value(self, key, value):
		self._client.set_value(key, value)
	
	def _setup_notification_listener(self):
		name = self._service.get_name()
		self._notification = NotificationListener(self._group, name)
		self._notification.add_listener(self._notify_model_change)
