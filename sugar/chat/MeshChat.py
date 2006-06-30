import logging
import random

from sugar.chat.GroupChat import GroupChat
from sugar.presence.Service import Service
import sugar.env

class MeshChat(GroupChat):
	SERVICE_TYPE = "_olpc_mesh_chat._udp"
	SERVICE_ADDRESS = "232.5.5.5"
	SERVICE_PORT = 6301

	def __init__(self):
		GroupChat.__init__(self)

		self._pservice.connect('service-appeared', self._service_appeared_cb)
		self._pservice.track_service_type(MeshChat.SERVICE_TYPE)

		self._publish()

		service = self._pservice.get_service(MeshChat.SERVICE_TYPE)
		if service is not None:
			self._service_appeared_cb(self._pservice, None, service)

	def _service_appeared_cb(self, pservice, buddy, service):
		if self._group_stream == None:
			if service.get_type() == MeshChat.SERVICE_TYPE:
				logging.debug('Mesh chat service appeared, setup the stream.')
				self._setup_stream(service)

	def _publish(self):
		service = Service(sugar.env.get_nick_name(), MeshChat.SERVICE_TYPE,
						  'local', MeshChat.SERVICE_ADDRESS, MeshChat.SERVICE_PORT)
		self._pservice.register_service(service)
