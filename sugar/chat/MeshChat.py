from sugar.chat.GroupChat import GroupChat
from sugar.presence.Service import Service
import sugar.env

class MeshChat(GroupChat):
	SERVICE_TYPE = "_olpc_mesh_chat._udp"
	SERVICE_ADDRESS = "232.5.5.5"
	SERVICE_PORT = 6301

	def __init__(self):
		GroupChat.__init__(self)

		service = Service(sugar.env.get_nick_name(), MeshChat.SERVICE_TYPE,
						  'local', MeshChat.SERVICE_ADDRESS, MeshChat.SERVICE_PORT)
		self._setup_stream(service)
